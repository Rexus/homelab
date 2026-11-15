"""Render one explicitly retained native Helm release for recovery inventory checks."""

import base64
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

import yaml

from flux_recovery_run import checksum, relative_file, write_private


PLATFORM_CHARTS = {'flux2', 'cilium', 'cert-manager', 'traefik', 'cloudnative-pg', 'barman-cloud',
                   'ceph-csi-rbd', 'ceph-csi-cephfs', 'csi-driver-nfs', 'nfs-subdir-external-provisioner',
                   'gitlab-runner'}
PRODUCT_CHARTS = {'gitlab': {'gitlab'}, 'harbor': {'harbor'}, 'netdata': {'netdata'},
                  'victoriametrics': {'victoria-metrics-single', 'victoria-metrics-cluster'},
                  'opensearch': {'opensearch'}, 'argocd': {'argo-cd'},
                  'vault-raft': {'vault'}, 'netbox-media': {'netbox'}}
CLUSTER_KINDS = {'Namespace', 'ClusterRole', 'ClusterRoleBinding', 'CustomResourceDefinition', 'StorageClass',
                 'CSIDriver', 'VolumeSnapshotClass', 'ValidatingWebhookConfiguration', 'MutatingWebhookConfiguration',
                 'APIService', 'IngressClass', 'PriorityClass', 'ClusterIssuer'}


def render_release(release, contract, objects, package, products, *, prepare=False):
    spec = release['spec']
    if hashlib.sha256(json.dumps(spec, sort_keys=True, separators=(',', ':')).encode()).hexdigest() != contract['spec_sha256']:
        raise ValueError('Reachable HelmRelease differs from its independently accepted native specification.')
    chart_spec = spec.get('chart', {}).get('spec', {})
    if spec.get('kubeConfig') or chart_spec.get('valuesFiles') or spec.get('upgrade', {}).get('preserveValues', False):
        raise ValueError('Recovery renders require this cluster and complete explicit native Helm values, without hidden previous values or chart value files.')
    if (chart_spec.get('chart') != contract['chart_name'] or chart_spec.get('version') != contract['version'] or
            spec.get('releaseName') != contract['release_name']):
        raise ValueError('Retained Helm contract differs from the actual reachable release chart/version/name.')
    archive = relative_file(package / 'artifacts', contract['archive'])
    locked = json.loads((package / 'artifact-lock.json').read_text())
    if not any(item['path'] == contract['archive'] and item['sha256'] == checksum(archive) for item in locked['files']):
        raise ValueError('Native chart archive differs from the independently verified artifact lock.')
    metadata = yaml.safe_load(subprocess.run(['helm', 'show', 'chart', str(archive)], check=True,
                                           capture_output=True, text=True, timeout=120).stdout)
    if metadata['name'] != contract['chart_name'] or metadata['version'] != contract['version']:
        raise ValueError('Retained chart archive contains a different native chart identity.')
    selected = [product for product in products if product['name'] == contract.get('product')]
    platform = contract.get('platform_chart', False)
    if platform:
        if selected or metadata['name'] not in PLATFORM_CHARTS:
            raise ValueError('Only recognized stateless native platform chart contracts can omit a data restore owner.')
    elif len(selected) != 1 or metadata['name'] not in PRODUCT_CHARTS.get(selected[0]['kind'], set()):
        raise ValueError('The reachable native data chart has no matching selected restore adapter.')
    namespace = spec.get('targetNamespace', release['metadata']['namespace'])
    if selected and selected[0].get('namespace', namespace) != namespace:
        raise ValueError('The native chart target namespace differs from its selected restore owner.')
    values = []
    for reference in spec.get('valuesFrom', []):
        if reference.get('targetPath') or reference.get('optional', False):
            raise ValueError('Recovery Helm value references require explicit retained whole YAML documents.')
        identity = (reference['kind'], release['metadata']['namespace'], reference['name'])
        if identity not in objects:
            raise ValueError('The retained source lacks the native Helm values Secret or ConfigMap.')
        resource = objects[identity]
        key = reference.get('valuesKey', 'values.yaml')
        content = resource.get('stringData', {}).get(key)
        if content is None:
            content = resource['data'][key]
            if reference['kind'] == 'Secret':
                content = base64.b64decode(content, validate=True).decode()
        values.append(yaml.safe_load(content))
    values.append(spec.get('values', {}))
    values_hash = hashlib.sha256(json.dumps(values, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    if prepare:
        contract['values_sha256'] = values_hash
    if values_hash != contract['values_sha256']:
        raise ValueError('Actual decrypted native Helm values differ from the accepted render contract.')
    with tempfile.TemporaryDirectory(prefix='native-recovery-chart-') as directory:
        root = Path(directory)
        argv = ['helm', 'template', contract['release_name'], str(archive), '--namespace', namespace,
                '--include-crds', '--skip-tests', '--kube-version', contract['kube_version']]
        if contract.get('is_upgrade', False):
            argv.append('--is-upgrade')
        for api_version in contract.get('api_versions', []):
            argv.extend(['--api-versions', api_version])
        for index, value in enumerate(values):
            path = root / f'values-{index}.yaml'
            path.write_text(yaml.safe_dump(value))
            path.chmod(0o600)
            argv.extend(['--values', str(path)])
        output = subprocess.run(argv, check=True, capture_output=True, text=True, timeout=120).stdout
        for index, renderer in enumerate(spec.get('postRenderers', [])):
            if set(renderer) != {'kustomize'} or set(renderer['kustomize']) - {'patches', 'images'}:
                raise ValueError('Use native Helm Kustomize patches/images in the accepted recovery contract.')
            stage = root / f'post-{index}'
            stage.mkdir()
            (stage / 'resources.yaml').write_text(output)
            (stage / 'kustomization.yaml').write_text(yaml.safe_dump({
                'apiVersion': 'kustomize.config.k8s.io/v1beta1', 'kind': 'Kustomization',
                'resources': ['resources.yaml'], **renderer['kustomize']}))
            output = subprocess.run(['kubectl', 'kustomize', str(stage)], check=True,
                                    capture_output=True, text=True, timeout=120).stdout
        rendered_hash = hashlib.sha256(output.encode()).hexdigest()
        if prepare:
            contract['render_sha256'] = rendered_hash
        if rendered_hash != contract['render_sha256']:
            raise ValueError('Native retained chart render differs from its independently accepted checksum.')
        documents = [item for item in yaml.load_all(output, Loader=yaml.CSafeLoader) if isinstance(item, dict)]
    for document in documents:
        if document['kind'] not in CLUSTER_KINDS:
            document.setdefault('metadata', {}).setdefault('namespace', namespace)
        document['_recovery_chart_owner'] = selected[0]['name'] if selected else None
        document['_recovery_platform_chart'] = platform
    return documents


def main():
    parser = argparse.ArgumentParser(description='Prepare a native Helm recovery contract locally for independent approval; no deployment occurs.')
    parser.add_argument('--release', type=Path, required=True, help='Actual native rendered HelmRelease YAML')
    parser.add_argument('--objects', type=Path, required=True, help='Retained decrypted native values Secrets/ConfigMaps YAML')
    parser.add_argument('--package', type=Path, required=True)
    parser.add_argument('--archive', required=True, help='Locked chart path below package artifacts/')
    parser.add_argument('--source', required=True, choices=['platform', 'tier1-platform', 'tier1-applications'])
    parser.add_argument('--kube-version', required=True)
    owner = parser.add_mutually_exclusive_group(required=True)
    owner.add_argument('--platform-chart', action='store_true')
    owner.add_argument('--product')
    parser.add_argument('--product-kind', choices=sorted(PRODUCT_CHARTS))
    parser.add_argument('--is-upgrade', action='store_true')
    parser.add_argument('--api-version', action='append', default=[])
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    release = yaml.safe_load(args.release.read_text())
    if release.get('kind') != 'HelmRelease' or not release.get('spec', {}).get('releaseName'):
        parser.error('Select the rendered HelmRelease with its explicit native releaseName.')
    if args.product and not args.product_kind:
        parser.error('--product requires --product-kind.')
    spec = release['spec']
    contract = dict(source=args.source, namespace=release['metadata']['namespace'], name=release['metadata']['name'],
        chart_name=spec['chart']['spec']['chart'], version=spec['chart']['spec']['version'],
        release_name=spec['releaseName'], archive=args.archive, kube_version=args.kube_version,
        api_versions=args.api_version, is_upgrade=args.is_upgrade,
        spec_sha256=hashlib.sha256(json.dumps(spec, sort_keys=True, separators=(',', ':')).encode()).hexdigest())
    contract.update({'platform_chart': True} if args.platform_chart else {'product': args.product})
    documents = []
    for item in yaml.safe_load_all(args.objects.read_text()):
        if isinstance(item, dict):
            documents.extend(item['items'] if item.get('kind') == 'List' else [item])
    objects = {(item['kind'], item.get('metadata', {}).get('namespace', ''), item['metadata']['name']): item for item in documents}
    products = [{'name': args.product, 'kind': args.product_kind}] if args.product else []
    render_release(release, contract, objects, args.package, products, prepare=True)
    write_private(args.output, json.dumps(contract, indent=2) + '\n')


if __name__ == '__main__':
    main()
