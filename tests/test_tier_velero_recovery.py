"""Native Velero orchestration against a loopback API, without CSI or a live restore."""

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import yaml

from backup_storage_api_support import BackupStorageAPI


ROOT = Path(__file__).resolve().parents[1]
ROLE = ROOT / 'tier-1/ansible/roles/platform_recovery'
ANSIBLE = os.environ.get('ANSIBLE_PLAYBOOK') or shutil.which('ansible-playbook')


class SnapshotAPI(BackupStorageAPI):
    resources = dict(BackupStorageAPI.resources,
                     backups=('Backup', True, 'velero.io/v1'), restores=('Restore', True, 'velero.io/v1'))

    def __init__(self):
        self.produced_claims = ['registry-data']
        super().__init__()

    def put(self, value):
        if value['kind'] == 'Restore':
            value['status'] = {'phase': 'Completed', 'errors': 0}
        super().put(value)
        if value['kind'] == 'Restore':
            for name in self.produced_claims:
                super().put({'apiVersion': 'v1', 'kind': 'PersistentVolumeClaim',
                    'metadata': {'namespace': 'harbor', 'name': name}, 'spec': {'volumeName': name + '-restored'}})


@unittest.skipUnless(ANSIBLE and os.name == 'posix', 'Requires native Ansible and kubernetes.core')
class VeleroClaimProof(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory(prefix='native-velero-proof-')))
        (self.root / 'receipts').mkdir()
        self.api = SnapshotAPI()
        self.addCleanup(self.api.close)
        self.config = self.root / 'kubeconfig'
        self.config.write_text(yaml.safe_dump(self.api.kubeconfig()))
        spec = {'includedNamespaces': ['harbor']}
        self.api.put({'apiVersion': 'velero.io/v1', 'kind': 'Backup',
            'metadata': {'name': 'retained', 'namespace': 'velero', 'uid': 'native-backup-uid'}, 'spec': spec,
            'status': {'phase': 'Completed', 'errors': 0, 'csiVolumeSnapshotsCompleted': 1, 'csiVolumeSnapshotsAttempted': 1}})
        self.product = {'name': 'harbor', 'namespace': 'harbor', 'backup_id': 'retained',
            'backup_uid': 'native-backup-uid', 'data_claims': ['registry-data'],
            'backup_spec_sha256': hashlib.sha256(json.dumps(spec, sort_keys=True).encode()).hexdigest()}

    def run_adapter(self, success=True):
        variables = {'ansible_python_interpreter': sys.executable, 'recovery_kubeconfig': str(self.config),
            'recovery_context': 'offline', 'recovery_product': self.product,
            'platform_recovery': {'workspace': str(self.root), 'plan_sha256': 'a' * 64, 'recovery_id': 'accepted'}}
        path = self.root / 'play.yml'
        path.write_text(yaml.safe_dump([{'hosts': 'localhost', 'connection': 'local', 'gather_facts': False,
            'vars': variables, 'tasks': [{'ansible.builtin.include_role': {'name': 'platform_recovery', 'tasks_from': 'velero'}}]}]))
        result = subprocess.run([ANSIBLE, '-i', 'localhost,', str(path)], capture_output=True, text=True, timeout=120,
            env=dict(os.environ, ANSIBLE_ROLES_PATH=str(ROLE.parent), ANSIBLE_LOCAL_TEMP=str(self.root / 'ansible-local')))
        self.assertEqual(result.returncode == 0, success, result.stdout + result.stderr)

    def creates(self):
        return sum(method == 'POST' and '/restores' in path for method, path, *_ in self.api.mutations)

    def test_completed_native_restore_requires_actual_claims_and_keeps_original_uids(self):
        self.run_adapter()
        self.run_adapter()
        self.assertEqual(self.creates(), 1)
        receipt = json.loads((self.root / 'receipts/harbor-velero.json').read_text())
        claim = self.api.objects['persistentvolumeclaims', 'harbor', 'registry-data']
        self.assertEqual(receipt['claims'], {'registry-data': claim['metadata']['uid']})
        claim['metadata']['uid'] = 'replacement-with-the-same-name'
        self.run_adapter(success=False)
        self.assertEqual(self.creates(), 1)

    def test_success_status_with_missing_or_unexpected_claims_cannot_unfence_consumers(self):
        for produced in ([], ['unexpected-claim']):
            with self.subTest(produced=produced):
                self.api.produced_claims = produced
                self.run_adapter(success=False)
                self.assertFalse((self.root / 'receipts/harbor-velero.json').exists())
                self.assertFalse(any('/deployments' in path for _, path, *_ in self.api.mutations))
                self.api.objects = {key: value for key, value in self.api.objects.items()
                                    if key[0] not in ('restores', 'persistentvolumeclaims')}

    def test_replaced_restore_and_unbound_claim_are_rejected_without_replaying_snapshot(self):
        self.run_adapter()
        claim = self.api.objects['persistentvolumeclaims', 'harbor', 'registry-data']
        claim['status']['phase'] = 'Pending'
        self.run_adapter(success=False)
        claim['status']['phase'] = 'Bound'
        restore = next(item for (kind, _, _), item in self.api.objects.items() if kind == 'restores')
        restore['metadata']['uid'] = 'replacement-restore'
        self.run_adapter(success=False)
        self.assertEqual(self.creates(), 1)


if __name__ == '__main__':
    unittest.main()
