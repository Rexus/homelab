"""Validate and stage the fixed Ansible platform recovery recipe.

Only accepted Git trees, checksum-bound private inputs and the existing recovery
roles are executable. The plan contains product/target data, never commands/hooks.
"""

import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import tarfile
import tempfile
from urllib.parse import urlsplit

import yaml


SHA256 = re.compile(r"[a-f0-9]{64}\Z")
COMMIT = re.compile(r"(?:[a-f0-9]{40}|[a-f0-9]{64})\Z")
NAME = re.compile(r"[a-z0-9][a-z0-9.-]{0,62}\Z")
PRODUCTS = {"spinnaker", "gitlab", "harbor", "victoriametrics", "cnpg-files", "opensearch", "argocd", "netdata",
            "vault-raft", "netbox-media"}
PREREQUISITES = {'Namespace', 'Secret', 'ConfigMap', 'Service', 'ServiceAccount', 'Role', 'RoleBinding',
                 'NetworkPolicy', 'PersistentVolumeClaim', 'PersistentVolume', 'StorageClass',
                 'Deployment', 'StatefulSet', 'Kustomization', 'HelmRelease'}
ENGINE_SUPPORT = {'Namespace', 'Secret', 'ConfigMap', 'Service', 'ServiceAccount', 'Role', 'RoleBinding',
                  'ClusterRole', 'ClusterRoleBinding', 'NetworkPolicy', 'CustomResourceDefinition',
                  'StorageClass', 'CSIDriver', 'VolumeSnapshotClass', 'BackupStorageLocation', 'VolumeSnapshotLocation'}


def checksum(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_private(path, text):
    content = text.encode('utf-8') if isinstance(text, str) else text
    with tempfile.NamedTemporaryFile(mode='wb', dir=path.parent, prefix='.recovery-', delete=False) as stream:
        temporary = Path(stream.name)
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())
    temporary.chmod(0o600)
    os.replace(temporary, path)


def relative_file(root, name):
    relative = Path(name)
    path = root / relative
    if (relative.is_absolute() or ".." in relative.parts or not relative.parts or
            any(part.is_symlink() for part in (path, *path.parents)) or not path.is_file()):
        raise ValueError("Retained input must be an existing regular file within its repository.")
    return path


def read_plan(path, expected, *, verify_custody=True):
    if not SHA256.fullmatch(expected) or checksum(path) != expected:
        raise ValueError("Recovery plan differs from the independently accepted SHA-256.")
    plan = json.loads(path.read_text())
    if plan.get("version") != 1 or plan.get("scope") not in ("tier1", "all-vms"):
        raise ValueError("Select recovery scope tier1 or all-vms in a version 1 plan.")
    if not NAME.fullmatch(plan.get("recovery_id", "")):
        raise ValueError("Select a stable DNS-safe recovery_id for this target and attempt.")
    package = plan["package"]
    for field in ("manifest_sha256", "artifact_lock_sha256"):
        if not SHA256.fullmatch(package[field]):
            raise ValueError("Bind the package manifest and artifact lock to accepted checksums.")
    if set(package["sources"]) != {"platform", "tier1-platform", "tier1-applications"}:
        raise ValueError("Bind all three independently retained Flux source commits.")
    if not all(COMMIT.fullmatch(commit) for commit in package["sources"].values()):
        raise ValueError("Source revisions must be full immutable commits.")
    required_tiers = {"tier-1", "shared"} | ({"tier-0"} if plan["scope"] == "all-vms" else set())
    repositories = plan["automation"]
    if set(repositories) != required_tiers:
        raise ValueError("Retain independent automation for Shared and each recovered tier.")
    basenames = [Path(source['directory']).name for source in repositories.values()]
    if len(set(basenames)) != len(basenames):
        raise ValueError("Retained generated repository sibling names must be distinct.")
    if any(Path(source['directory']).name in repositories and Path(source['directory']).name != name
           for name, source in repositories.items()):
        raise ValueError("A generated repository alias conflicts with another recovery owner.")
    for name, source in repositories.items():
        root = Path(source["directory"]).resolve(strict=True)
        if not COMMIT.fullmatch(source["commit"]):
            raise ValueError("Automation must identify its exact retained Git commit.")
        actual = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"],
                                check=True, capture_output=True, text=True).stdout.strip()
        if actual != source["commit"]:
            raise ValueError("Retained automation checkout is at a different revision.")
        subprocess.run(["git", "-C", str(root), "diff", "--quiet", "HEAD", "--"], check=True)
        for entry in source.get("private_files", []):
            original = relative_file(root, entry["path"])
            if not SHA256.fullmatch(entry["sha256"]) or checksum(original) != entry["sha256"]:
                raise ValueError("Private input, key or original state differs from retained custody.")
    retained = {name + '/' + entry['path'] for name, source in repositories.items()
                for entry in source.get('private_files', [])}
    for field in ("inventory", "recovery_git_inputs"):
        if plan[field] not in retained:
            raise ValueError("Inventory and recovery source inputs must be checksum-bound private files.")
    if not plan.get('artifact_supply'):
        raise ValueError("Declare native publication of retained artifacts to an independent recovery supply.")
    for artifact in plan['artifact_supply']:
        if artifact['kind'] not in ('oci', 'helm') or '..' in Path(artifact['path']).parts:
            raise ValueError("Select a locked OCI archive or Helm package for native publication.")
        if artifact.get('auth_file') not in retained or not artifact.get('destination'):
            raise ValueError("Retain independent recovery-supply credentials and exact artifact destinations.")
        if not SHA256.fullmatch(artifact.get('digest', '')):
            raise ValueError("Bind each published image/chart to its independently accepted OCI manifest digest.")
        if artifact.get('tier', 1) not in {cluster['tier'] for cluster in plan['clusters']}:
            raise ValueError("Every recovery publication must select its package's cluster tier.")
    if any(not any('/.terraform/state/' in ('/' + item) for item in retained if item.startswith(tier + '/'))
           for tier in required_tiers - {'shared'}):
        raise ValueError("Retain the original Terraform state of every recovered tier separately from working copies.")
    vms = plan.get("virtual_machines", [])
    if (len({cluster['tier'] for cluster in plan['clusters']}) != len(plan['clusters']) or
            not any(cluster['tier'] == 1 for cluster in plan['clusters'])):
        raise ValueError("Select one target per tier, including the owned Tier 1 cluster.")
    if len({vm["vmid"] for vm in vms}) != len(vms):
        raise ValueError("Declare each restored VM exactly once.")
    if any(vm["tier"] not in (0, 1) or not 100 <= int(vm["vmid"]) <= 999999999 for vm in vms):
        raise ValueError("Select explicit Tier 0/1 VMIDs from the original inventory.")
    if plan["scope"] == "tier1" and any(vm["tier"] != 1 for vm in vms):
        raise ValueError("Tier 1 recovery cannot alter Tier 0 VMs.")
    for vm in vms:
        if not NAME.fullmatch(vm["node"]) or not SHA256.fullmatch(vm["backup_config_sha256"]):
            raise ValueError("Every VM backup requires its node and retained configuration checksum.")
        if not re.fullmatch(r"[A-Za-z0-9_-]+:backup/[A-Za-z0-9_.:/-]+", vm["backup"]):
            raise ValueError("Select an exact native Proxmox backup volume, including its backup ID.")
        if not vm.get("network") or not NAME.fullmatch(vm["recovery_bridge"]):
            raise ValueError("Every target needs explicit isolated recovery NIC configurations.")
        if vm.get('role') != 'prerequisite':
            raise ValueError("Kubernetes VM backups cannot be booted by this workflow. Select clean Talos reconstruction.")
        if not vm.get('health_checks'):
            raise ValueError("Every prerequisite VM needs native TCP or verified HTTPS readiness gates before cluster reconstruction.")
        for check in vm['health_checks']:
            if check.get('kind') not in ('tcp', 'https') or not 1 <= int(check.get('timeout', 300)) <= 900:
                raise ValueError("Select bounded native TCP or HTTPS prerequisite readiness checks.")
            if check['kind'] == 'tcp' and (not check.get('host') or not 1 <= int(check.get('port', 0)) <= 65535):
                raise ValueError("Prerequisite TCP readiness requires the actual private host and listener port.")
            if check['kind'] == 'https' and (not check.get('url', '').startswith('https://') or check.get('status') != 200):
                raise ValueError("Prerequisite HTTP readiness requires an expected verified HTTPS success response.")
            for field in ('ca_path', 'headers_file'):
                if field in check and check[field] not in retained:
                    raise ValueError("Retain prerequisite verification trust and credentials independently.")
        for nic, configuration in vm["network"].items():
            if not re.fullmatch(r"net[0-9]+", nic) or not isinstance(configuration, str):
                raise ValueError("Recovery NIC names must be net0, net1, etc.")
            if f"bridge={vm['recovery_bridge']}" not in configuration.split(","):
                raise ValueError("All restored NICs must use the accepted isolated recovery bridge.")
    for cluster in plan["clusters"]:
        if cluster['tier'] == 1:
            cluster.setdefault('package', package)
            cluster.setdefault('recovery_git_inputs', plan['recovery_git_inputs'])
        if cluster["tier"] not in (0, 1) or f"tier-{cluster['tier']}" not in repositories:
            raise ValueError("Cluster tier must belong to this reconstruction scope.")
        if cluster['tier'] == 0:
            owned_package = cluster.get('package', {})
            if (set(owned_package.get('sources', {})) != {'platform', 'tier1-platform', 'tier1-applications'} or
                    any(not COMMIT.fullmatch(value) for value in owned_package['sources'].values()) or
                    any(not SHA256.fullmatch(owned_package.get(field, ''))
                        for field in ('manifest_sha256', 'artifact_lock_sha256')) or
                    not owned_package.get('directory')):
                raise ValueError("Tier 0 needs its independently accepted package and distinct platform commit.")
            if cluster.get('recovery_git_inputs') not in retained:
                raise ValueError("Retain independent Tier 0 recovery Git service inputs.")
            cutover = cluster.get('cutover', {})
            if (set(cutover.get('sources', {})) != {'platform'} or cutover.get('resume_roots') != ['platform'] or
                    not cutover.get('health_checks')):
                raise ValueError("Tier 0 requires its own normal source, platform resume and workload health contract.")
            for source in cutover['sources'].values():
                validate_source_handoff(source, retained)
        if not cluster.get("context") or not cluster["api_server"].startswith("https://"):
            raise ValueError("Bind every restored Kubernetes context to its private API endpoint.")
        if cluster.get('mode') != 'clean' or not cluster.get('previous_namespace_uid'):
            raise ValueError("Select clean reconstruction and retain the former kube-system UID to reject old etcd.")
        if not SHA256.fullmatch(cluster.get('canary_sha256', '')):
            raise ValueError("Retain the bootstrap canary checksum before resuming its independent root.")
        if not cluster.get('bootstrap_images') or any(not isinstance(image, str) or not image for image in cluster['bootstrap_images']):
            raise ValueError("Retain all resolved Talos machine-configuration image references in bootstrap_images.")
        state_relative = f"tier-{cluster['tier']}/.terraform/state/talos/terraform.tfstate"
        if state_relative not in retained:
            raise ValueError("Retain the existing Talos backend state, including its original secret resource.")
        from recovery_talos import secrets_identity
        state_root = Path(repositories[f"tier-{cluster['tier']}"]['directory'])
        secrets_identity(json.loads(relative_file(state_root, '.terraform/state/talos/terraform.tfstate').read_text()))
        for field in ('bootstrap_inputs', 'provider_environment', 'restore_resources'):
            if cluster.get(field) not in retained:
                raise ValueError("Retain bootstrap, provider environment and recovery-only resources with checksums.")
        if cluster.get('restore_engines') and cluster['restore_engines'] not in retained:
            raise ValueError("Native restore-engine manifests must be independently retained and checksum-bound.")
        if cluster['kubeconfig'] != f"tier-{cluster['tier']}/secrets/talos/kubeconfig":
            raise ValueError("Use the credentials exported by the existing Talos reconstruction entry point.")
        if not NAME.fullmatch(cluster.get('recovery_bridge', '')) or not cluster.get('nodes'):
            raise ValueError("Declare exact target node names/VMIDs and their isolated recovery network.")
        if len({node['vmid'] for node in cluster['nodes']}) != len(cluster['nodes']):
            raise ValueError("Clean reconstruction requires unique target VMIDs.")
        fields = ['bootstrap_inputs', 'restore_resources'] + (['restore_engines'] if cluster.get('restore_engines') else [])
        for field in fields:
            repository, _, relative = cluster[field].partition('/')
            documents = list(yaml.safe_load_all(relative_file(Path(repositories[repository]['directory']), relative).read_text()))
            if field == 'bootstrap_inputs':
                inputs = documents[0]
                if (not isinstance(inputs, dict) or inputs.get('cluster_platform_action') != 'apply' or
                        inputs.get('cluster_platform_flux_recovery') is not True or
                        (cluster['tier'] == 1 and inputs.get('cluster_platform_flux_applications_suspended') is not True)):
                    raise ValueError("Retain recovery-only bootstrap inputs with application reconciliation suspended.")
                if inputs.get('cluster_platform_flux_commit') != cluster['package']['sources']['platform']:
                    raise ValueError("Each bootstrap must fetch its own independently accepted platform commit.")
                if cluster['tier'] == 1 and inputs.get('cluster_platform_flux_platform_commit') != package['sources']['tier1-platform']:
                    raise ValueError("Tier 1 bootstrap must fetch its separately accepted service source commit.")
            elif field == 'restore_resources':
                for document in documents:
                    if not isinstance(document, dict):
                        continue
                    if document.get('kind') not in PREREQUISITES:
                        raise ValueError("Recovery prerequisites require a supported native passive resource or stopped workload kind.")
                    if document.get('kind') in ('Deployment', 'StatefulSet') and document.get('spec', {}).get('replicas', 1) != 0:
                        raise ValueError("Recovery product prerequisites must hold consumers at zero replicas.")
                    if document.get('kind') in ('Kustomization', 'HelmRelease') and document.get('spec', {}).get('suspend') is not True:
                        raise ValueError("Recovery reconciliation prerequisites must be suspended.")
            else:
                allowed = {(item.get('kind', 'Deployment'), item['namespace'], item['name'])
                           for item in cluster.get('restore_engine_health', [])}
                for document in documents:
                    if not isinstance(document, dict):
                        raise ValueError("Retain actual native restore engine resources.")
                    kind = document.get('kind')
                    if kind in ENGINE_SUPPORT:
                        continue
                    metadata = document.get('metadata', {})
                    if kind not in ('Deployment', 'DaemonSet') or (kind, metadata.get('namespace'), metadata.get('name')) not in allowed:
                        raise ValueError("Restore engines allow only passive native support and explicitly health-gated operator/CSI/Velero workloads.")
                    pod = document.get('spec', {}).get('template', {}).get('spec', {})
                    if not pod.get('containers') or any(not re.search(r'@sha256:[a-f0-9]{64}$', item.get('image', ''))
                            for item in pod['containers'] + pod.get('initContainers', [])):
                        raise ValueError("Restore-engine workloads need independently retained image digests.")
    if plan['scope'] == 'all-vms' and not any(cluster['tier'] == 0 for cluster in plan['clusters']):
        raise ValueError("Whole-platform recovery must reconstruct Tier 0 prerequisites first.")
    if plan['scope'] == 'all-vms' and not plan.get('template_rebuild'):
        raise ValueError("Whole-platform reconstruction must rebuild its exact retained Talos templates first.")
    if plan['scope'] == 'all-vms':
        source_owners = []
        for cluster in plan['clusters']:
            repository, _, relative = cluster['recovery_git_inputs'].partition('/')
            inputs = yaml.safe_load(relative_file(Path(repositories[repository]['directory']), relative).read_text())
            source_owners.append((inputs.get('flux_recovery_git_root'), inputs.get('flux_recovery_git_user')))
        if (any(not root or not user for root, user in source_owners) or
                len({root for root, _ in source_owners}) != len(source_owners) or
                len({user for _, user in source_owners}) != len(source_owners)):
            raise ValueError("Each cluster needs distinct retained read-only Git service roots and identities.")
    if 'template_rebuild' in plan:
        templates = plan['template_rebuild']
        if templates.get('catalog') not in retained or templates.get('provider_environment') not in retained or not templates.get('assets'):
            raise ValueError("Retain the original template catalog, publisher credentials and locked image assets.")
        if 'tier-0/.terraform/state/proxmox-templates/terraform.tfstate' not in retained:
            raise ValueError("Retain original template publication state before rebuilding its VMIDs.")
        if any(Path(asset).is_absolute() or '..' in Path(asset).parts for asset in templates['assets'].values()):
            raise ValueError("Template image assets must stay within the accepted package's artifact directory.")
    products = plan.get("products", [])
    if not products or len({p["name"] for p in products}) != len(products):
        raise ValueError("List each selected product once with its native backup and target.")
    for product in products:
        product.setdefault('tier', 1)
        if product["kind"] not in PRODUCTS or not NAME.fullmatch(product["name"]):
            raise ValueError("Product has no implemented native restore adapter.")
        if product.get("tier", 1) not in {cluster["tier"] for cluster in plan["clusters"]}:
            raise ValueError("Every product needs an accepted target cluster.")
        if not product.get("backup_id") or not product.get("checks") or not product.get("writers"):
            raise ValueError("Every native restore needs an exact backup, actual writers and content/denial checks.")
        common = {'namespace', 'namespace_uid', 'verification_ca_secret', 'verification_headers_secret'}
        required = {
            'spinnaker': {'restic_image', 'restic_secret', 'mysql', 'redis', 'orca_url', 'admin_headers_secret', 'secrets_file', 'operating_component'},
            'gitlab': {'image', 'toolbox', 'edition', 'secrets_file', 'gitlab_recovery'},
            'harbor': {'backup_uid', 'backup_spec_sha256', 'secrets_file', 'data_claims'},
            'victoriametrics': {'image', 'claim', 'credentials_secret'},
            'cnpg-files': {'inputs', 'system_identifier', 'secrets_file', 'cnpg_cluster'},
            'opensearch': {'url', 'repository', 'backup_uid', 'indices', 'client_cert', 'client_key', 'ca_path',
                           'restore_workloads', 'data_claims', 'claim_uids', 'repository_spec_file'},
            'argocd': {'backup_uid', 'backup_spec_sha256', 'secrets_file', 'data_claims'},
            'netdata': {'backup_uid', 'backup_spec_sha256', 'secrets_file', 'data_claims'},
            'vault-raft': {'vault', 'control_backup', 'data_claims', 'claim_uids'},
            'netbox-media': {'media', 'control_backup', 'data_claims', 'claim_uids', 'restic_image', 'restic_secret', 'restic_version'},
        }[product['kind']] | common
        if any(field not in product or product[field] in ('', None) for field in required):
            raise ValueError("Native product recovery inputs are incomplete. Check the product contract before target mutation.")
        if product['kind'] in ('harbor', 'argocd', 'netdata'):
            if not product['data_claims'] or any(not NAME.fullmatch(claim) for claim in product['data_claims']):
                raise ValueError("List the exact native snapshot-restored data claims.")
            owner = next(cluster for cluster in plan['clusters'] if cluster['tier'] == product['tier'])
            if not owner.get('restore_engines') or not owner.get('restore_engine_health'):
                raise ValueError("Velero recovery requires retained native engine manifests and exact rollout health gates.")
            if not SHA256.fullmatch(product['backup_spec_sha256']):
                raise ValueError("Bind the native backup catalog specification to its independent checksum.")
        if not any('content_sha256' in check for check in product['checks']) or not any(
                check['status'] in (401, 403) for check in product['checks']):
            raise ValueError("Every product needs retained-content and denied-access checks before cutover.")
        for field in ('secrets_file', 'inputs', 'client_cert', 'client_key', 'ca_path', 'network_policy_file', 'repository_spec_file'):
            if field in product and product[field] not in retained:
                raise ValueError("Product credentials and recovery inputs must be independently checksum-bound.")
        if '@sha256:' not in product.get('python_image', ''):
            raise ValueError("Retain each native verification worker image independently by digest.")
        forbidden = {'orca', 'echo', 'clouddriver', 'delivery-promotion-authority'}
        if any(workload['name'] in forbidden for workload in product.get('verification_workloads', [])):
            raise ValueError("Verification cannot activate delivery executors or request triggers.")
        if any(not check['url'].startswith('https://') for check in product['checks']):
            raise ValueError("Recovery checks must use the selected verified HTTPS endpoints.")
        for check in product['checks']:
            if any(check[field] not in retained for field in ('ca_path', 'headers_file') if field in check):
                raise ValueError("Recovery-check trust and credentials must be independently checksum-bound.")
            if 'content_sha256' in check and not SHA256.fullmatch(check['content_sha256']):
                raise ValueError("Recovery content checks require an accepted SHA-256.")
        for writer in product["writers"]:
            if writer["kind"] not in ("Deployment", "StatefulSet", "CronJob") or not NAME.fullmatch(writer["name"]):
                raise ValueError("Select exact application writer resources.")
        if product['kind'] == 'cnpg-files' and not NAME.fullmatch(product['cnpg_cluster']):
            raise ValueError("Bind CNPG restoration to its exact native cluster name.")
        if product['kind'] == 'gitlab':
            native = product['gitlab_recovery']
            fields = ('api_url', 'ca_file', 'ca_sha256', 'admin_headers_file', 'admin_headers_sha256',
                      'sidekiq_workloads')
            if not isinstance(native, dict) or any(not native.get(field) for field in fields):
                raise ValueError('Complete the native GitLab recovery API and isolated Sidekiq contract.')
            endpoint = urlsplit(native['api_url'])
            if (endpoint.scheme != 'https' or not endpoint.hostname or endpoint.username or endpoint.password or
                    endpoint.path not in ('', '/') or endpoint.query or endpoint.fragment):
                raise ValueError('GitLab recovery requires its isolated verified HTTPS origin.')
            for path_field, hash_field in (('ca_file', 'ca_sha256'), ('admin_headers_file', 'admin_headers_sha256')):
                expected = next((entry['sha256'] for owner, source in repositories.items()
                                 for entry in source.get('private_files', [])
                                 if owner + '/' + entry['path'] == native[path_field]), None)
                if expected is None or native[hash_field] != expected:
                    raise ValueError('GitLab API trust and administrator headers must match retained private-file checksums.')
            workers = native['sidekiq_workloads']
            writers = {(item['kind'], item['name']) for item in product['writers']}
            verification = {(item['kind'], item['name']) for item in product.get('verification_workloads', [])}
            if (not isinstance(workers, list) or not workers or
                    any(worker.get('kind') not in ('Deployment', 'StatefulSet') or
                        not NAME.fullmatch(worker.get('name', '')) or
                        (worker['kind'], worker['name']) not in writers or
                        (worker['kind'], worker['name']) in verification for worker in workers) or
                    len({(item['kind'], item['name']) for item in workers}) != len(workers)):
                raise ValueError('Select exact fenced Sidekiq workloads outside normal verification consumers.')
        if product['kind'] in ('vault-raft', 'netbox-media'):
            from recovery_control import validate as validate_control_product
            validate_control_product(product, verify_custody=verify_custody)
        if product['kind'] == 'opensearch':
            if not product['url'].startswith('https://'):
                raise ValueError("OpenSearch recovery requires its isolated verified HTTPS endpoint.")
            for field in ('repository', 'backup_id'):
                if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*', product[field]):
                    raise ValueError("Bind OpenSearch to one exact repository and snapshot name.")
            indices = product['indices']
            if (not isinstance(indices, list) or not indices or len(set(indices)) != len(indices) or
                    any(not re.fullmatch(r'[a-z0-9.][a-z0-9._-]*', index) or
                        index == '.opendistro_security' or index.startswith('.security') for index in indices)):
                raise ValueError("Select exact application index names, excluding wildcards and security indices.")
            claims = product['data_claims']
            if (not isinstance(claims, list) or not claims or len(set(claims)) != len(claims) or
                    any(not NAME.fullmatch(claim) for claim in claims) or
                    not isinstance(product['claim_uids'], dict) or
                    set(product['claim_uids']) != set(claims) or
                    any(not isinstance(uid, str) or not uid for uid in product['claim_uids'].values())):
                raise ValueError("Bind every OpenSearch data claim to its retained UID or a newly owned claim.")
            workloads = product['restore_workloads']
            writers = {(writer['kind'], writer['name']) for writer in product['writers']}
            if (not isinstance(workloads, list) or not workloads or
                    len({item['name'] for item in workloads}) != len(workloads) or
                    any(item.get('kind') != 'StatefulSet' or not NAME.fullmatch(item.get('name', '')) or
                        type(item.get('replicas')) is not int or item['replicas'] < 1 or
                        ('StatefulSet', item['name']) not in writers for item in workloads)):
                raise ValueError("OpenSearch restoration may start only explicitly selected writer StatefulSets with positive replica counts.")
            repository, _, relative = product['repository_spec_file'].partition('/')
            specification = yaml.safe_load(relative_file(Path(repositories[repository]['directory']), relative).read_text())
            if (not isinstance(specification, dict) or not specification.get('type') or
                    not isinstance(specification.get('settings'), dict) or specification['settings'].get('readonly') is not True):
                raise ValueError("Retain a native OpenSearch repository specification with settings.readonly set to true.")
        if product["kind"] == "spinnaker":
            component = Path(product['operating_component'])
            if component.is_absolute() or '..' in component.parts or not component.parts:
                raise ValueError("Select the accepted generated Spinnaker component within the platform source.")
            if not SHA256.fullmatch(product["backup_id"]):
                raise ValueError("Spinnaker requires the full independent restic snapshot ID.")
            for database in ("mysql", "redis"):
                backup = product[database]
                if not {'image', 'path', 'sha256', 'claim', 'claim_uid'}.issubset(backup):
                    raise ValueError("Bind every database file, native tool image and clean PVC identity.")
                if (not SHA256.fullmatch(backup["sha256"]) or "@sha256:" not in backup["image"] or
                        ".." in Path(backup["path"]).parts):
                    raise ValueError("Bind each SQL/RDB file and native restore image to retained identities.")
                if not backup.get('claim_uid'):
                    raise ValueError("Retain the exact clean target PVC UID before destructive restoration.")
            if not product['orca_url'].startswith('https://'):
                raise ValueError("Native cancellation requires the isolated verified HTTPS Orca endpoint.")
            required_writers = {'gate', 'echo', 'orca', 'spinnaker-mysql', 'spinnaker-redis'}
            if not required_writers.issubset({writer['name'] for writer in product['writers']}):
                raise ValueError("Spinnaker restoration must stop Gate, Echo, Orca, MySQL and Redis.")
            if "@sha256:" not in product['restic_image']:
                raise ValueError("Retain the independently available restic image by digest.")
    if any(product['kind'] == 'spinnaker' for product in products) and 'promotion_authority' not in plan:
        raise ValueError("Spinnaker recovery must rotate independently retained promotion authority tickets.")
    if 'promotion_authority' in plan:
        authority = plan['promotion_authority']
        if authority['secret_file'] not in retained or not SHA256.fullmatch(authority['new_ticket_key_sha256']):
            raise ValueError("Retain the replacement promotion authority identity independently.")
        if authority['new_ticket_key_sha256'] == authority['previous_ticket_key_sha256']:
            raise ValueError("Recovery must invalidate pending authority tickets with a new retained key.")
    if 'cutover' in plan:
        if any(product['kind'] == 'spinnaker' for product in products) and plan['cutover'].get('resume_roots') != [
                'platform', 'tier1-platform', 'tier1-applications']:
            raise ValueError("Spinnaker operation requires all three normal source roots in dependency order.")
        if set(plan['cutover'].get('sources', {})) != {'platform', 'tier1-platform', 'tier1-applications'}:
            raise ValueError("Cutover must restore all three native Git source ownership URLs and accepted refs.")
        for source in plan['cutover']['sources'].values():
            validate_source_handoff(source, retained)
        selected = {(vm['node'], vm['vmid']): set(vm['network']) for vm in vms}
        for cluster in plan['clusters']:
            for node in cluster['nodes']:
                key = (node['node'], node['vmid'])
                if key in selected:
                    raise ValueError("A cluster node cannot reuse a prerequisite VMID.")
                selected[key] = {'net0'}
        cutover_targets = set()
        for vm in plan['cutover'].get('virtual_machines', []):
            key = (vm['node'], vm['vmid'])
            if key not in selected or key in cutover_targets:
                raise ValueError("Cutover can address each restored VM only once.")
            cutover_targets.add(key)
            if {nic['name'] for nic in vm['network']} != selected[key]:
                raise ValueError("Cutover must retain the complete restored VM NIC inventory.")
            for nic in vm['network']:
                if not isinstance(nic['configuration'], str) or not any(
                        entry.startswith('bridge=') for entry in nic['configuration'].split(',')):
                    raise ValueError("Cutover requires an explicit desired network for every restored NIC.")
        if cutover_targets != set(selected):
            raise ValueError("Cutover must explicitly account for every recovered VM.")
        if not set(plan['cutover'].get('resume_roots', [])).issubset({'platform', 'tier1-platform', 'tier1-applications'}):
            raise ValueError("Cutover cannot resume another tier or unrelated Flux scope.")
        if plan['cutover'].get('resume_roots', [])[:1] != ['platform']:
            raise ValueError("Resume the independent bootstrap root and its canary before service/application roots.")
        if not plan['cutover'].get('health_checks'):
            raise ValueError("Cutover requires actual selected workload health checks.")
    return plan


def validate_source_handoff(source, retained):
    if not source['url'].startswith('ssh://') or not source.get('ref') or not NAME.fullmatch(source.get('secret_name', '')):
        raise ValueError("Cutover needs the restored SSH repository, exact accepted ref and native source Secret name.")
    subprocess.run(['git', 'check-ref-format', source['ref']], check=True, capture_output=True)
    if source.get('ensure_ref', 'verify') not in ('verify', 'restore-with-lease'):
        raise ValueError("Select native Git ref verification or explicit lease-bound administrative restoration.")
    if source.get('ensure_ref') == 'restore-with-lease' and not COMMIT.fullmatch(source.get('expected_remote_head', '')):
        raise ValueError("Retain the restored native Git branch head before approving a lease-bound update.")
    if any(source.get(field) not in retained for field in ('identity_file', 'known_hosts_file', 'secret_file')):
        raise ValueError("Retain native Git source trust and credentials for the restored owner.")


def stage_repository(source, target):
    """Extract only the accepted tree and copy checksum-bound private inputs once."""
    root = Path(source["directory"]).resolve(strict=True)
    archive = subprocess.run(["git", "-C", str(root), "archive", source["commit"]],
                             capture_output=True, check=True).stdout
    target.mkdir(parents=True, exist_ok=True, mode=0o700)
    with tarfile.open(fileobj=io.BytesIO(archive)) as stream:
        for member in stream:
            relative = Path(member.name)
            if member.issym() or member.islnk() or member.isdev() or relative.is_absolute() or ".." in relative.parts:
                raise ValueError("Automation archive contains a linked or escaping member.")
            destination = target / relative
            if any(part.is_symlink() for part in (destination, *destination.parents)):
                raise ValueError("Staged automation contains a linked destination path.")
            if member.isdir():
                destination.mkdir(parents=True, exist_ok=True, mode=0o700)
            elif member.isfile():
                content = stream.extractfile(member).read()
                if destination.exists():
                    if destination.read_bytes() != content:
                        raise ValueError("Staged automation changed during recovery.")
                else:
                    destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                    write_private(destination, content)
                destination.chmod(member.mode & 0o700)
    for entry in source.get("private_files", []):
        content = relative_file(root, entry['path']).read_bytes()
        if hashlib.sha256(content).hexdigest() != entry['sha256']:
            raise ValueError("Original recovery input changed before staging.")
        destination = target / entry["path"]
        if any(part.is_symlink() for part in (destination, *destination.parents)):
            raise ValueError("Staged recovery input contains a linked destination path.")
        if destination.exists():
            if checksum(destination) != entry["sha256"]:
                if entry['path'] == '.terraform/state/talos/terraform.tfstate':
                    from recovery_talos import secrets_identity
                    original_state = json.loads(content)
                    if secrets_identity(json.loads(destination.read_text())) != secrets_identity(original_state):
                        raise ValueError("Working Talos state changed the original cluster secret identity.")
                elif entry['path'] == '.terraform/state/proxmox-templates/terraform.tfstate':
                    original_state = json.loads(content)
                    current_state = json.loads(destination.read_text())
                    if current_state.get('lineage') != original_state.get('lineage') or current_state.get('version') != 4:
                        raise ValueError("Working template state lost its original backend identity.")
                else:
                    raise ValueError("Recovery working inputs changed. Retain them and select a new target.")
            continue
        destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        write_private(destination, content)


def run_recovery(args, verify_package):
    os.umask(0o077)
    completed = args.workspace.resolve() / 'receipts/cutover.json'
    completed_plan = json.loads(completed.read_text()) if completed.exists() else {}
    # A completed read-only audit rechecks live identities/content without bringing Shamir shares online.
    read_only_audit = args.phase == 'resume' and completed_plan.get('plan_sha256') == args.expect_plan
    plan = read_plan(args.plan, args.expect_plan, verify_custody=not read_only_audit)
    package = Path(plan["package"]["directory"]).resolve(strict=True)
    import argparse
    packages = {1: plan['package'], **{cluster['tier']: cluster['package']
                for cluster in plan['clusters'] if cluster['tier'] == 0}}
    for tier, owned_package in packages.items():
        directory = Path(owned_package['directory']).resolve(strict=True)
        if checksum(directory / 'manifest.json') != owned_package['manifest_sha256']:
            raise ValueError("Recovery package manifest changed after acceptance.")
        verify_package(argparse.Namespace(directory=directory, expect_lock=owned_package['artifact_lock_sha256'],
                       expect=[f"{name}={commit}" for name, commit in owned_package['sources'].items()]))
        locked = json.loads((directory / 'artifact-lock.json').read_text())
        if any(artifact['path'] not in {entry['path'] for entry in locked['files']}
               for artifact in plan['artifact_supply'] if artifact.get('tier', 1) == tier):
            raise ValueError("Published recovery artifacts must belong to their tier's verified independent artifact lock.")
        if tier == 1 and plan.get('template_rebuild') and not set(plan['template_rebuild']['assets'].values()).issubset(
                {entry['path'] for entry in locked['files']}):
            raise ValueError("Every rebuilt template image must belong to the independently verified artifact lock.")
    workspace = args.workspace.resolve()
    if any(workspace == Path(source["directory"]).resolve() or
           workspace.is_relative_to(Path(source["directory"]).resolve()) for source in plan["automation"].values()):
        raise ValueError("Recovery workspace must be separate from original automation and Terraform state.")
    workspace.mkdir(parents=True, exist_ok=True, mode=0o700)
    # Native Linux advisory locking prevents two recovery operators from sharing one journal.
    import fcntl
    with (workspace / ".recovery.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        marker = workspace / "accepted-plan.sha256"
        if marker.exists() and marker.read_text().strip() != args.expect_plan:
            raise ValueError("This workspace belongs to another accepted plan.")
        if not marker.exists() and any(path.name != ".recovery.lock" for path in workspace.iterdir()):
            raise ValueError("Use a new empty workspace for recovery.")
        write_private(marker, args.expect_plan + "\n")
        for name, source in plan["automation"].items():
            stage_repository(source, workspace / name)
            # Generated wrappers retain their original sibling repository names.
            basename = Path(source['directory']).name
            alias = workspace / basename
            if basename != name:
                if alias.exists() and alias.resolve() != (workspace / name).resolve():
                    raise ValueError("Generated repository sibling name conflicts with the recovery workspace.")
                if not alias.exists():
                    alias.symlink_to(workspace / name, target_is_directory=True)
        inputs = workspace / "recovery-inputs.json"
        effective = dict(plan, plan_sha256=args.expect_plan, workspace=str(workspace), package_directory=str(package),
                         phase=args.phase)
        if args.phase == 'resume' and not plan.get('cutover'):
            raise ValueError("Resume requires an independently accepted cutover contract in the same plan.")
        completed = workspace / 'receipts/cutover.json'
        if completed.exists():
            receipt = json.loads(completed.read_text())
            if receipt.get('plan_sha256') != args.expect_plan:
                raise ValueError("Completed cutover belongs to another plan.")
            if args.phase != 'resume':
                raise ValueError("Recovery already completed. Repeat --phase resume for read-only target/content verification.")
            effective['phase'] = 'verify'
        write_private(inputs, json.dumps({"platform_recovery": effective}, indent=2) + "\n")
        target = workspace / "tier-1"
        environment = dict(os.environ, ANSIBLE_CONFIG=str(target / "ansible/ansible.cfg"))
        subprocess.run(["ansible-playbook", "-i", str(workspace / plan["inventory"]),
                        str(target / "ansible/playbooks/maintenance/platform-recovery.yml"),
                        "-e", "@" + str(inputs)], cwd=target, env=environment, check=True)
