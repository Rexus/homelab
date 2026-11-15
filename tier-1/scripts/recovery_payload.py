#!/usr/bin/env python3
"""Inspect the accepted generated Spinnaker operating graph using native Kustomize."""

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

import yaml

from flux_recovery_run import write_private, checksum, relative_file
from recovery_helm import render_release


SERVICES = {'clouddriver', 'deck', 'echo', 'fiat', 'front50', 'gate', 'orca', 'rosco'}
PASSIVE = {'Namespace', 'Secret', 'ConfigMap', 'Service', 'ServiceAccount', 'Role', 'RoleBinding',
           'ClusterRole', 'ClusterRoleBinding', 'NetworkPolicy', 'CustomResourceDefinition', 'StorageClass',
           'PersistentVolume', 'Ingress', 'IngressClass', 'CSIDriver', 'VolumeSnapshotClass',
           'GitRepository', 'HelmRepository', 'OCIRepository', 'Kustomization', 'Certificate', 'Issuer',
           'ClusterIssuer', 'Middleware', 'ServersTransport', 'CiliumNetworkPolicy', 'CiliumClusterwideNetworkPolicy'}
PASSIVE.update({'ValidatingWebhookConfiguration', 'MutatingWebhookConfiguration', 'APIService', 'PriorityClass',
                'PodDisruptionBudget', 'HorizontalPodAutoscaler', 'ServiceMonitor', 'PodMonitor', 'PrometheusRule',
                'ValidatingAdmissionPolicy', 'ValidatingAdmissionPolicyBinding'})


def inspect_inventory(documents, products, tier):
    """Refuse source-wide persistence or initializers outside the native restore selection."""
    selected = [product for product in products if product.get('tier', 1) == tier]
    claims = set()
    for product in selected:
        kind = product['kind']
        if kind in ('harbor', 'argocd', 'netdata', 'opensearch', 'vault-raft'):
            claims.update((product['namespace'], name) for name in product.get('data_claims', []))
        elif kind == 'victoriametrics':
            claims.add((product['namespace'], product['claim']))
        elif kind == 'netbox-media':
            claims.add((product['namespace'], product['media']['claim']))
        elif product.get('data_claims'):
            raise ValueError('This native adapter does not restore arbitrary additional persistent claims.')
        if product['kind'] == 'spinnaker':
            claims.update((product['namespace'], product[database]['claim']) for database in ('mysql', 'redis'))
        if product.get('repository_claim'):
            claims.add((product['namespace'], product['repository_claim']))
    for resource in documents:
        kind = resource.get('kind')
        namespace = resource.get('metadata', {}).get('namespace', '')
        name = resource.get('metadata', {}).get('name', '')
        if kind in PASSIVE or not kind:
            continue
        if kind == 'HelmRelease':
            raise ValueError('Final recovery sources require native rendered chart objects for persistence inspection. An opaque HelmRelease cannot establish restore coverage.')
        if kind == 'PersistentVolumeClaim':
            if (namespace, name) not in claims:
                raise ValueError('Final source contains an uncovered persistent data claim: ' + namespace + '/' + name)
            continue
        if kind == 'Cluster' and resource.get('apiVersion', '').startswith('postgresql.cnpg.io/'):
            matches = [product for product in selected if product['kind'] == 'cnpg-files' and
                       product['namespace'] == namespace and product.get('cnpg_cluster') == name]
            if not matches or 'initdb' in resource.get('spec', {}).get('bootstrap', {}):
                raise ValueError('Final source contains an uncovered CNPG database or fresh initializer.')
            continue
        if kind not in ('Deployment', 'StatefulSet', 'DaemonSet', 'Job', 'CronJob'):
            raise ValueError('Final source has no inspected native restore contract for resource kind ' + kind)
        pod = resource.get('spec', {}).get('template', {}).get('spec', {})
        if kind == 'CronJob':
            pod = resource['spec']['jobTemplate']['spec']['template']['spec']
        # Native Runner managers are restored as stopped configuration. Even a newly
        # registered manager must not poll retained jobs during initial source handoff.
        labels = resource.get('metadata', {}).get('labels', {})
        runner = ('gitlab-runner' in pod.get('serviceAccountName', '') or
                  any('gitlab-runner' in str(value) for value in labels.values()) or
                  any('gitlab-runner' in container.get('name', '') or
                      '/gitlab-runner' in container.get('image', '')
                      for container in pod.get('containers', [])))
        if runner and (kind not in ('Deployment', 'StatefulSet') or resource['spec'].get('replicas', 1) != 0):
            raise ValueError('Accepted recovery sources must keep ordinary GitLab Runner managers stopped until a separate operating change.')
        references = [volume['persistentVolumeClaim']['claimName'] for volume in pod.get('volumes', [])
                      if 'persistentVolumeClaim' in volume]
        for claim in resource.get('spec', {}).get('volumeClaimTemplates', []):
            references.extend(claim['metadata']['name'] + '-' + name + '-' + str(index)
                              for index in range(resource['spec'].get('replicas', 1)))
        if any((namespace, claim) not in claims for claim in references):
            raise ValueError('Final workload references data outside the native restore inventory: ' + namespace + '/' + name)
        if kind in ('Job', 'CronJob'):
            if resource.get('_recovery_platform_chart') or resource.get('_recovery_chart_owner'):
                # Native chart identity, values and complete output are checked before reaching this inventory.
                # The data adapter restores its claims before these selected, version-matched hooks resume.
                continue
            owner = any(product['kind'] == 'spinnaker' and product['namespace'] == namespace for product in selected)
            approved = name.startswith(('spinnaker-data-mysql-adopt-', 'spinnaker-data-redis-adopt-',
                'spinnaker-databases-verify-', 'spinnaker-backup-verify-', 'spinnaker-repository-')) or name == 'spinnaker-backup'
            if not owner or not approved:
                raise ValueError('Final source contains an uncovered initializer or scheduled Job: ' + namespace + '/' + name)
            for container in pod.get('containers', []) + pod.get('initContainers', []):
                for entry in container.get('env', []):
                    if ((entry['name'] == 'SPINNAKER_DATABASE_ACTION' and entry.get('value') != 'verify') or
                            (entry['name'] in ('BACKUP_FILESYSTEM_INITIALIZE', 'BACKUP_ALLOW_INITIALIZE') and entry.get('value') != 'false')):
                        raise ValueError('Final source still enables fresh data initialization.')


def render(root, relative):
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError('The generated operating stage escapes the accepted source.')
    check_local_build(root.resolve(), path)
    result = subprocess.run(['kubectl', 'kustomize', str(path)], check=True,
                            capture_output=True, text=True, timeout=120)
    return [document for document in yaml.safe_load_all(result.stdout) if isinstance(document, dict)]


def check_local_build(root, path, visited=None):
    visited = set() if visited is None else visited
    path = path.resolve()
    if path in visited:
        return
    visited.add(path)
    if not path.is_relative_to(root):
        raise ValueError('Kustomize resources must remain within the independently retained source.')
    if path.is_file():
        return
    configuration = next((path / name for name in ('kustomization.yaml', 'kustomization.yml', 'Kustomization')
                          if (path / name).is_file()), None)
    if configuration is None:
        raise ValueError('A selected recovery directory lacks its native Kustomization.')
    value = yaml.safe_load(configuration.read_text())
    for reference in value.get('resources', []) + value.get('components', []) + value.get('bases', []):
        if not isinstance(reference, str) or '://' in reference or reference.startswith(('git::', 'github.com/', 'gitlab.com/')):
            raise ValueError('Recovery Kustomize builds cannot fetch unretained remote resources.')
        check_local_build(root, path / reference, visited)


def retained_input(plan, name):
    repository, _, relative = name.partition('/')
    entries = plan['automation'].get(repository, {}).get('private_files', [])
    expected = next((entry['sha256'] for entry in entries if entry['path'] == relative), None)
    path = relative_file(Path(plan['workspace']) / repository, relative)
    if expected is None or checksum(path) != expected:
        raise ValueError('Recovery source input is not independently checksum-bound: ' + name)
    return path


def verify_authority_epoch(documents, plan):
    """Reject a normal source that would reactivate the pre-recovery ticket identity."""
    if 'promotion_authority' not in plan:
        return
    authority = plan['promotion_authority']
    original = yaml.safe_load(retained_input(plan, authority['secret_file']).read_text())
    namespace = 'delivery-promotion-authority'
    if original.get('kind') != 'Secret' or original.get('metadata', {}).get('namespace') != namespace:
        raise ValueError('Retain the replacement promotion authority Secret in its original namespace.')
    name = original['metadata']['name']
    selected = [item for item in documents if item.get('kind') == 'Secret' and
                item.get('metadata', {}).get('namespace') == namespace and item['metadata'].get('name') == name]
    if not selected:
        raise ValueError('The operating source must retain the replacement promotion authority ticket epoch.')
    for secret in [original, *selected]:
        content = secret.get('stringData', {}).get('ticket-key')
        key = content.encode('utf-8') if isinstance(content, str) else base64.b64decode(
            secret.get('data', {}).get('ticket-key', ''), validate=True)
        if hashlib.sha256(key).hexdigest() != authority['new_ticket_key_sha256']:
            raise ValueError('The operating source must retain the replacement promotion authority ticket epoch.')
    deployments = [item for item in documents if item.get('kind') == 'Deployment' and
                   item.get('metadata', {}).get('namespace') == namespace and
                   item['metadata'].get('name') == 'delivery-promotion-authority']
    if not deployments or any(
            [volume.get('secret', {}).get('secretName') for volume in
             item['spec']['template']['spec'].get('volumes', []) if volume.get('name') == 'authority'] != [name]
            for item in deployments):
        raise ValueError('The operating authority must mount the retained replacement ticket Secret.')


def decrypt_document(document, plan, cluster, source):
    if 'sops' not in document:
        return document
    key = retained_input(plan, cluster.get('source_age_keys', {}).get(source, ''))
    result = subprocess.run(['sops', '--decrypt', '--input-type', 'json', '--output-type', 'json', '/dev/stdin'],
        input=json.dumps(document), text=True, capture_output=True, check=True, timeout=60,
        env=dict(os.environ, SOPS_AGE_KEY_FILE=str(key)))
    return json.loads(result.stdout)


def reachable_inventory(roots, paths, plan, cluster):
    """Use native Kustomize builds and follow only the selected Flux source graph."""
    if set(paths) != set(roots):
        raise ValueError('Declare source_paths for each selected independent source, matching bootstrap inputs.')
    queue, visited, documents = list(paths.items()), set(), []
    while queue:
        source, path = queue.pop(0)
        identity = (source, path)
        if identity in visited:
            continue
        visited.add(identity)
        for document in render(roots[source], path):
            document = decrypt_document(document, plan, cluster, source)
            items = document['items'] if document.get('kind') == 'List' else [document]
            for item in items:
                item['_recovery_source'] = source
                if item.get('kind') == 'Kustomization' and item.get('apiVersion', '').startswith('kustomize.toolkit.fluxcd.io/'):
                    spec = item['spec']
                    if any(spec.get(field) for field in ('postBuild', 'patches', 'images', 'components', 'targetNamespace', 'commonMetadata')):
                        raise ValueError('Recovery requires native generated Flux paths without additional runtime transformations.')
                    reference = spec.get('sourceRef', {})
                    owner = reference.get('name', '')
                    if reference.get('kind', 'GitRepository') != 'GitRepository' or owner not in roots:
                        raise ValueError('Reachable Flux configuration selects an unretained source.')
                    if not spec.get('suspend', False) or item['metadata']['name'] in cluster.get('cutover', plan.get('cutover', {})).get('resume_roots', []):
                        queue.append((owner, spec['path']))
                documents.append(item)
    objects = {(item.get('kind'), item.get('metadata', {}).get('namespace', ''), item.get('metadata', {}).get('name')): item
               for item in documents}
    contracts = {(entry['source'], entry['namespace'], entry['name']): entry for entry in cluster.get('helm_releases', [])}
    expanded = []
    for item in documents:
        if item.get('kind') != 'HelmRelease':
            expanded.append(item)
            continue
        if item.get('spec', {}).get('suspend', False):
            continue
        identity = (item['_recovery_source'], item['metadata']['namespace'], item['metadata']['name'])
        if identity not in contracts:
            raise ValueError('Reachable HelmRelease needs a retained native chart render contract: ' + '/'.join(identity))
        expanded.extend(render_release(item, contracts[identity], objects,
            Path(cluster.get('package', plan['package'])['directory']),
            [product for product in plan['products'] if product['tier'] == cluster['tier']]))
    return expanded


def verify_images(documents, plan, cluster):
    supplied = [item for item in plan['artifact_supply'] if item['kind'] == 'oci' and item.get('tier', 1) == cluster['tier']]
    references = set(cluster.get('bootstrap_images', []))
    for product in plan['products']:
        if product['tier'] != cluster['tier']:
            continue
        references.update(product[field] for field in ('image', 'restic_image', 'python_image') if field in product)
        if product['kind'] == 'spinnaker':
            references.update(product[database]['image'] for database in ('mysql', 'redis'))
        if product['kind'] == 'vault-raft':
            references.add(product['vault']['image'])
    for item in documents:
        spec = item.get('spec', {})
        if item.get('kind') == 'CronJob':
            spec = spec.get('jobTemplate', {}).get('spec', {})
        pod = spec.get('template', {}).get('spec', {})
        if item.get('kind') == 'Cluster' and spec.get('imageName'):
            references.add(spec['imageName'])
        references.update(container['image'] for container in pod.get('containers', []) + pod.get('initContainers', []) if 'image' in container)
    for image in references:
        matches = [item for item in supplied if image == item['destination'] + '@sha256:' + item['digest'] or
                   image == item.get('source_image')]
        if len(matches) != 1:
            raise ValueError('Required recovery image has no unique locked independent supply: ' + image)
        entry = matches[0]
        if image != entry['destination'] + '@sha256:' + entry['digest']:
            reference = image.split('@', 1)[0]
            domain, separator, repository = reference.partition('/')
            if not separator or ('.' not in domain and ':' not in domain and domain != 'localhost'):
                domain, repository = 'docker.io', reference if separator else 'library/' + reference
            mirror = cluster.get('registry_mirrors', {}).get(domain)
            if not mirror or entry['destination'] != mirror + '/' + repository.rsplit(':', 1)[0]:
                raise ValueError('Original image requires the retained native Talos mirror and matching repository path: ' + image)
            if '@sha256:' in image:
                if image.split('@sha256:', 1)[1] != entry['digest']:
                    raise ValueError('Retained image digest differs from its source reference.')
            elif entry.get('tag') != repository.rsplit(':', 1)[-1] or ':' not in repository:
                raise ValueError('A tagged source image requires the same independently published tag.')


def inspect_component(root, product):
    graph = render(root, product['operating_component'])
    resources = []
    for stage in graph:
        if (stage.get('kind') != 'Kustomization' or
                stage.get('apiVersion') != 'kustomize.toolkit.fluxcd.io/v1' or
                stage['spec'].get('sourceRef', {}).get('name') != 'tier1-platform' or
                stage['spec'].get('suspend', False)):
            raise ValueError('Select the generated active tier1-platform operating component graph.')
        resources.extend(render(root, stage['spec']['path']))
    selected = [item for item in resources if item.get('metadata', {}).get('namespace') == product['namespace']]
    guards = [item for item in selected if item.get('kind') == 'Job' and
              item['metadata']['name'].startswith(('spinnaker-data-mysql-', 'spinnaker-data-redis-'))]
    if (len(guards) != 2 or any('-adopt-' not in item['metadata']['name'] for item in guards) or
            any('persistentVolumeClaim' in volume for item in guards
                for volume in item['spec']['template']['spec'].get('volumes', []))):
        raise ValueError('Final Spinnaker source must use native adopt network guards over restored running databases.')
    databases = [item for item in selected if item.get('kind') == 'Job' and
                 item['metadata']['name'].startswith('spinnaker-databases-')]
    actions = [entry.get('value') for item in databases
               for container in item['spec']['template']['spec']['containers']
               for entry in container.get('env', []) if entry['name'] == 'SPINNAKER_DATABASE_ACTION']
    if len(databases) != 1 or actions != ['verify']:
        raise ValueError('The accepted operating payload must verify existing SQL schemas.')
    deployments = [item for item in selected if item.get('kind') == 'Deployment']
    by_name = {item['metadata']['name']: item for item in deployments}
    if not SERVICES.issubset(by_name) or any(by_name[name]['spec'].get('replicas', 1) < 1 for name in SERVICES):
        raise ValueError('The accepted operating payload must start every native Spinnaker consumer.')
    ingress = [item for item in selected if item.get('kind') == 'Ingress']
    if not ingress:
        raise ValueError('The accepted operating payload must publish the normal Spinnaker ingress.')
    return [{'tier': product.get('tier', 1), 'api_version': item['apiVersion'], 'kind': item['kind'],
             'namespace': item['metadata']['namespace'], 'name': item['metadata']['name'], 'spec': item['spec']}
            for item in deployments + ingress]


def operating_resources(plan):
    products = [item for item in plan['products'] if item['kind'] == 'spinnaker']
    result = []
    with tempfile.TemporaryDirectory(prefix='accepted-operating-') as directory:
        for cluster in plan['clusters']:
            selected_package = cluster.get('package', plan['package'])
            package = Path(selected_package['directory'])
            manifest = json.loads((package / 'manifest.json').read_text())
            names = ['platform'] if cluster['tier'] == 0 else ['platform', 'tier1-platform', 'tier1-applications']
            roots = {}
            for name in names:
                source = manifest['sources'][name]
                if source['commit'] != selected_package['sources'][name]:
                    raise ValueError('Operating payload differs from the accepted source commit.')
                root = Path(directory) / ('tier-' + str(cluster['tier'])) / name
                root.parent.mkdir(parents=True, exist_ok=True)
                subprocess.run(['git', 'clone', '--quiet', '--no-checkout', str(package / source['bundle']), str(root)],
                               check=True, capture_output=True, timeout=120)
                subprocess.run(['git', '-C', str(root), 'checkout', '--quiet', '--detach', source['commit']],
                               check=True, capture_output=True, timeout=120)
                roots[name] = root
            bootstrap = yaml.safe_load(retained_input(plan, cluster['bootstrap_inputs']).read_text())
            paths = {'platform': bootstrap.get('cluster_platform_flux_path', '')}
            if cluster['tier'] == 1:
                paths.update({'tier1-platform': bootstrap.get('cluster_platform_flux_platform_path', './clusters/tier1/platform'),
                              'tier1-applications': bootstrap.get('cluster_platform_flux_application_path', './clusters/tier1/applications')})
            if any(not path for path in paths.values()):
                raise ValueError('Retain the exact native bootstrap source paths before recovery.')
            documents = reachable_inventory(roots, paths, plan, cluster)
            inspect_inventory(documents, plan['products'], cluster['tier'])
            if cluster['tier'] == 1:
                verify_authority_epoch(documents, plan)
            for field in ('restore_resources', 'restore_engines'):
                if cluster.get(field):
                    documents.extend(item for item in yaml.safe_load_all(retained_input(plan, cluster[field]).read_text())
                                     if isinstance(item, dict))
            verify_images(documents, plan, cluster)
            if cluster['tier'] == 1:
                result.extend(resource for product in products for resource in inspect_component(roots['tier1-platform'], product))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    plan = json.loads(args.inputs.read_text())['platform_recovery']
    resources = operating_resources(plan)
    write_private(args.output, json.dumps({'plan_sha256': plan['plan_sha256'], 'resources': resources}) + '\n')


if __name__ == '__main__':
    main()
