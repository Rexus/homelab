#!/usr/bin/env python3
"""Rebuild an absent Talos cluster from its retained secrets and a working state copy."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import ssl
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPSHandler, ProxyHandler

import yaml


def write_receipt(path, record):
    """Keep a complete checkpoint through a controller interruption."""
    with tempfile.NamedTemporaryFile(mode='w', dir=path.parent, prefix='.reconstruction-', delete=False) as stream:
        temporary = Path(stream.name)
        json.dump(record, stream)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    temporary.chmod(0o600)
    os.replace(temporary, path)


def secrets_identity(state):
    records = [resource for resource in state.get('resources', [])
               if resource.get('type') == 'talos_machine_secrets' and resource.get('name') == 'cluster']
    if len(records) != 1 or len(records[0].get('instances', [])) != 1:
        raise ValueError('Retain exactly one original Talos cluster secret resource.')
    attributes = records[0]['instances'][0]['attributes']
    if not attributes.get('machine_secrets') or not attributes.get('client_configuration'):
        raise ValueError('Original Talos machine secrets and administrative identity are missing.')
    return hashlib.sha256(json.dumps(attributes, sort_keys=True).encode()).hexdigest()


def runtime_addresses(state):
    addresses = []
    runtime = {'proxmox_virtual_environment_vm', 'talos_machine_configuration_apply',
               'talos_machine_bootstrap', 'talos_cluster_kubeconfig'}
    for resource in state.get('resources', []):
        if resource.get('type') not in runtime or resource.get('mode') != 'managed':
            continue
        if resource.get('module'):
            raise ValueError('This recovery adapter accepts the existing root Talos resources only.')
        for instance in resource.get('instances', []):
            address = resource['type'] + '.' + resource['name']
            if 'index_key' in instance:
                address += '[' + json.dumps(instance['index_key']) + ']'
            addresses.append(address)
    return addresses


def proxmox_configuration(environment, node):
    endpoint = environment['PROXMOX_VE_ENDPOINT'].rstrip('/')
    parsed = urlsplit(endpoint)
    if parsed.scheme != 'https' or parsed.path or parsed.username or parsed.query or parsed.fragment:
        raise ValueError('Retain a verified HTTPS Proxmox root endpoint.')
    context = ssl.create_default_context(cafile=environment.get('SSL_CERT_FILE') or None)
    client = build_opener(ProxyHandler({}), HTTPSHandler(context=context))
    request = Request(endpoint + f"/api2/json/nodes/{node['node']}/qemu/{node['vmid']}/config",
                      headers={'Authorization': 'PVEAPIToken=' + environment['PROXMOX_VE_API_TOKEN']})
    try:
        with client.open(request, timeout=30) as response:
            return json.loads(response.read())['data']
    except HTTPError as error:
        body = error.read().decode(errors='replace')
        if error.code == 500 and ('does not exist' in body or 'no such' in body.lower()):
            return None
        raise ValueError('Cannot verify the selected native Proxmox VM identity.') from error


def validate_plan(plan, cluster):
    changes = plan.get('resource_changes', [])
    nodes = {node['name']: node for node in cluster['nodes']}
    observed = set()
    configurations = set()
    for resource in changes:
        actions = resource.get('change', {}).get('actions', [])
        if 'delete' in actions:
            raise ValueError('Recovery cannot destroy or replace an existing infrastructure resource.')
        if resource['type'] == 'talos_machine_secrets':
            if actions != ['no-op']:
                raise ValueError('Recovery cannot initialize or replace the retained Talos secret identity.')
        if resource['type'] == 'talos_machine_configuration_apply' and 'bootstrap_images' in cluster:
            index = resource.get('index')
            if index not in nodes or index in configurations:
                raise ValueError('Every Talos machine configuration must select one distinct accepted node.')
            documents = list(yaml.safe_load_all(resource['change']['after'].get('machine_configuration_input', '')))
            machine = next((item['machine'] for item in documents if isinstance(item, dict) and 'machine' in item), None)
            if machine is None:
                raise ValueError('The resolved Talos machine configuration is required before provisioning.')
            def images(value):
                if isinstance(value, dict):
                    return [image for key, child in value.items() for image in
                            ([child] if key == 'image' and isinstance(child, str) else images(child))]
                if isinstance(value, list):
                    return [image for child in value for image in images(child)]
                return []
            if set(images(documents)) - set(cluster['bootstrap_images']):
                raise ValueError('A resolved native Talos image is missing from independent bootstrap supply.')
            registries = machine.get('registries', {})
            for registry, endpoint in cluster.get('registry_mirrors', {}).items():
                mirrors = [item for item in documents if isinstance(item, dict) and
                           item.get('kind') == 'RegistryMirrorConfig' and item.get('name') == registry]
                roots = [item for item in documents if isinstance(item, dict) and
                         item.get('kind') == 'RegistryTLSConfig' and item.get('name') == endpoint]
                legacy = registries.get('mirrors', {}).get(registry)
                if mirrors:
                    valid = (len(mirrors) == 1 and len(roots) <= 1 and legacy is None and
                             mirrors[0].get('skipFallback') is True and
                             [item.get('url') for item in mirrors[0].get('endpoints', [])] == ['https://' + endpoint] and
                             not any(item.get('overridePath', False) for item in mirrors[0].get('endpoints', [])) and
                             not any(item.get('insecureSkipVerify', False) for item in roots))
                else:
                    tls = registries.get('config', {}).get(endpoint, {}).get('tls', {})
                    legacy = legacy or {}
                    valid = (legacy.get('endpoints') == ['https://' + endpoint] and
                             legacy.get('skipFallback') is True and not legacy.get('overridePath', False) and
                             not tls.get('insecureSkipVerify', False))
                if not valid:
                    raise ValueError('Resolved Talos registry mirrors must use only the accepted verified independent endpoint.')
            configurations.add(index)
        if resource['type'] != 'proxmox_virtual_environment_vm':
            continue
        after = resource['change']['after']
        name = after['name']
        if name not in nodes or name in observed:
            raise ValueError('Saved plan contains an undeclared or duplicate cluster VM.')
        node = nodes[name]
        if after['vm_id'] != node['vmid'] or after['node_name'] != node['node']:
            raise ValueError('Saved plan differs from the selected target VMID or hypervisor.')
        networks = after.get('network_device', [])
        if not networks or any(nic['bridge'] != cluster['recovery_bridge'] for nic in networks):
            raise ValueError('Cluster VM creation must use the accepted isolated recovery network.')
        observed.add(name)
    if observed != set(nodes):
        raise ValueError('Saved plan does not account for the complete selected cluster.')
    if 'bootstrap_images' in cluster and configurations != set(nodes):
        raise ValueError('The saved plan must resolve every selected Talos configuration before provisioning.')


def recover(args):
    plan = json.loads(args.inputs.read_text())['platform_recovery']
    cluster = next(item for item in plan['clusters'] if item['tier'] == args.tier)
    if cluster['mode'] != 'clean':
        raise ValueError('Kubernetes recovery supports clean reconstruction with retained Talos identity.')
    repo = Path(plan['workspace']) / f'tier-{args.tier}'
    state_path = repo / '.terraform/state/talos/terraform.tfstate'
    original = json.loads(state_path.read_text())
    identity = secrets_identity(original)
    receipt = Path(plan['workspace']) / 'receipts' / f'tier-{args.tier}-reconstruction.json'
    previous = json.loads(receipt.read_text()) if receipt.exists() else None
    if previous and (previous['plan_sha256'] != plan['plan_sha256'] or previous['secrets_sha256'] != identity):
        raise ValueError('Working state no longer has the accepted original Talos identity.')
    loader = Path(plan['workspace']) / 'shared/scripts/lib/provider-environment.sh'
    environment_file = Path(plan['workspace']) / cluster['provider_environment']
    loaded = subprocess.run(['bash', '-ec',
        'source "$1"; env_file_path="$2"; load_env_file >&2; map_provider_env >&2; check_provider_env >&2; env -0',
        'recovery-provider', str(loader), str(environment_file)], check=True, capture_output=True)
    environment = dict(os.environ)
    environment.update(entry.split('=', 1) for entry in loaded.stdout.decode().split('\0') if entry)
    endpoint = environment['TF_VAR_proxmox_api_url']
    token = environment['TF_VAR_proxmox_api_token_id'] + '=' + environment['TF_VAR_proxmox_api_token_secret']
    if environment.get('PROXMOX_VE_ENDPOINT', endpoint) != endpoint or environment.get('PROXMOX_VE_API_TOKEN', token) != token:
        raise ValueError('Retained native and alias Proxmox credentials conflict.')
    environment['PROXMOX_VE_ENDPOINT'] = endpoint
    environment['PROXMOX_VE_API_TOKEN'] = token
    environment['TF_IN_AUTOMATION'] = '1'
    environment['TF_DATA_DIR'] = str(repo / '.terraform/data/talos')
    root = repo / 'terraform/deployments/kubernetes'
    marker = 'recovery=' + plan['plan_sha256']
    root.mkdir(parents=True, exist_ok=True)
    override = root / 'zz_recovery_override.tf'
    override_text = ('resource "proxmox_virtual_environment_vm" "node" {\n'
                     '  description = ' + json.dumps(marker) + '\n}\n')
    if override.exists() and override.read_text() != override_text:
        raise ValueError('The working recovery ownership override changed.')
    override.write_text(override_text)
    observed = {}
    for node in cluster['nodes']:
        actual = proxmox_configuration(environment, node)
        if actual is None:
            continue
        if not previous or actual.get('name') != node['name'] or actual.get('description') != marker:
            raise ValueError('A target VM exists outside this exact clean reconstruction attempt.')
        identity_fields = {key: actual.get(key) for key in ('vmgenid', 'smbios1')}
        if not any(identity_fields.values()):
            raise ValueError('The native VM has no recorded generation/SMBIOS identity.')
        if previous.get('vm_identities') and previous['vm_identities'].get(node['name']) != identity_fields:
            raise ValueError('A reconstructed VM was replaced between recovery stages.')
        observed[node['name']] = identity_fields

    def command(*argv):
        result = subprocess.run(list(argv), cwd=repo, env=environment,
                                capture_output=True, text=True, timeout=3600)
        diagnostics = receipt.with_suffix('.native.log')
        with diagnostics.open('a') as stream:
            diagnostics.chmod(0o600)
            stream.write(json.dumps({'argv': argv, 'returncode': result.returncode}) + '\n')
            if 'pull' not in argv and '-json' not in argv:
                stream.write(result.stdout)
            stream.write(result.stderr)
        if result.returncode:
            raise ValueError('Native reconstruction failed. Inspect private diagnostics at ' + str(diagnostics))
        return result

    command('terraform', '-chdir=' + str(root), 'init', '-input=false', '-lockfile=readonly',
            '-reconfigure', '-backend-config=path=' + str(state_path))
    if not previous:
        archive = receipt.with_suffix('.before.tfstate')
        if not archive.exists():
            archive.write_text(command('terraform', '-chdir=' + str(root), 'state', 'pull').stdout)
            archive.chmod(0o600)
        addresses = runtime_addresses(original)
        if addresses:
            command('terraform', '-chdir=' + str(root), 'state', 'rm', *addresses)
        # Retain the secret identity and record preparation before any new VM can be created.
        current = json.loads(command('terraform', '-chdir=' + str(root), 'state', 'pull').stdout)
        if secrets_identity(current) != identity:
            raise ValueError('Original Talos identity changed while preparing the working state.')
        write_receipt(receipt, {'version': 1, 'plan_sha256': plan['plan_sha256'],
                               'secrets_sha256': identity, 'phase': 'prepared', 'vm_identities': observed})
    command('bash', 'scripts/kubernetes-cluster.sh', 'plan')
    saved = repo / '.terraform/plans/talos.tfplan'
    saved_sha256 = hashlib.sha256(saved.read_bytes()).hexdigest()
    proposed = json.loads(command('terraform', '-chdir=' + str(root), 'show', '-json', str(saved)).stdout)
    validate_plan(proposed, cluster)
    if hashlib.sha256(saved.read_bytes()).hexdigest() != saved_sha256:
        raise ValueError('The saved plan changed after validation. No infrastructure apply was started.')
    command('bash', 'scripts/kubernetes-cluster.sh', 'apply')
    command('bash', 'scripts/kubernetes-cluster.sh', 'credentials')
    actual = json.loads(command('terraform', '-chdir=' + str(root), 'state', 'pull').stdout)
    if secrets_identity(actual) != identity:
        raise ValueError('Reconstruction changed the original Talos administrative identity.')
    vm_identities = {}
    for node in cluster['nodes']:
        actual_vm = proxmox_configuration(environment, node)
        if actual_vm is None or actual_vm.get('name') != node['name'] or actual_vm.get('description') != marker:
            raise ValueError('Native reconstruction did not produce the selected owned VM.')
        vm_identities[node['name']] = {key: actual_vm.get(key) for key in ('vmgenid', 'smbios1')}
        if not any(vm_identities[node['name']].values()):
            raise ValueError('Native reconstruction did not retain a VM generation identity.')
    write_receipt(receipt, {'version': 1, 'plan_sha256': plan['plan_sha256'],
                           'secrets_sha256': identity, 'phase': 'provisioned', 'vm_identities': vm_identities})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs', required=True, type=Path)
    parser.add_argument('--tier', required=True, type=int, choices=[0, 1])
    args = parser.parse_args()
    recover(args)


if __name__ == '__main__':
    main()
