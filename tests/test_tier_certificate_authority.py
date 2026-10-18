"""CA runtime ownership and generated references preserve controlled signing boundaries."""

import yaml

from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM


class CertificateAuthorityContracts(TierRepositoryTestCase):
    def test_design_and_generated_reference_preserve_separate_ca_functions(self):
        self.generate()
        for docs in (UPSTREAM / 'docs', self.root / 'verify-architecture/docs/auto-docs'):
            design = (docs / 'architecture/cryptography/certificate-authority.md').read_text()
            for expected in ('OpenXPKI Community', 'permanent infrastructure issuer',
                             'Root -->|Signs subordinate CA certificate offline| Infrastructure',
                             'Root -->|Signs subordinate CA certificate offline| Identity',
                             'Enterprise-only', 'acme2certifier', 'DataVault', 'missing signing identity'):
                self.assertIn(expected, design)
            self.assertIn('Vault remains a secret service', design)
            reference = (docs / 'architecture/reference-platform.md').read_text()
            self.assertIn('OpenXPKI on ca-1', reference)
            self.assertIn('Enrollment -->|Authenticated issuer interface| Issuer', reference)
            self.assertIn('FreeIPA identity CA', reference)

    def test_guides_name_actual_iac_and_controlled_integration_gates(self):
        self.generate()
        for docs in (UPSTREAM / 'docs', self.root / 'verify-architecture/docs/auto-docs'):
            issuer = (docs / 'deployment/stage-2-trust/procedures/issuer.md').read_text()
            for expected in ('<prefix>-tier-0', 'deployment/openxpki.yml', 'template_vm_id',
                             'foundation --plan-only', 'foundation --terraform-only',
                             'extra-disk input', 'Debian 12', '2028-06-30', 'openxpki_required_state_paths'):
                self.assertIn(expected, issuer)
            self.assertNotIn('bash scripts/deploy.sh openxpki', issuer)
            identity = (docs / 'deployment/stage-3-identity-runtime/procedures/freeipa.md').read_text()
            for expected in ('## External CA integration gate', 'two-phase install',
                             'ipareplica_setup_ca: true', 'ipaserver_external_ca'):
                self.assertIn(expected, identity)
            offline = (docs / 'deployment/stage-2-trust/procedures/offline-root.md').read_text()
            self.assertIn('Keep `root_ca` empty', offline)
            self.assertIn('clca does not support concurrent writers', offline)
            operations = (docs / 'administration/cryptography/certificate-authority.md').read_text()
            self.assertIn('--playbook maintenance/openxpki.yml', operations)
            self.assertIn('Revocation', operations)
        self.assertTrue((UPSTREAM / 'tier-0/ansible/roles/openxpki/tasks/main.yml').exists())
        self.assertNotIn('openxpki', (UPSTREAM / 'tier-0/.deployment-setups').read_text().splitlines())
        variables = yaml.safe_load((UPSTREAM / 'tier-0/ansible/group_vars/foundation.yml.example').read_text())
        self.assertNotIn('ipaserver_external_ca', variables)
        self.assertTrue(variables['ipareplica_setup_ca'])
        self.assertEqual(variables['foundation_freeipa_ca_mode'], 'internal')

    def test_generated_owned_design_and_hidden_checklist_keep_their_boundaries(self):
        self.generate()
        owned = self.root / 'verify-tier-0/docs/architecture/README.md'
        self.assertIn('Draft: OpenXPKI', owned.read_text())
        owned.write_text('# Selected site-specific CA\n')
        self.generate('--refresh')
        self.assertEqual(owned.read_text(), '# Selected site-specific CA\n')
        checklist = (UPSTREAM / '.ai/ca-implementation.md').read_text()
        self.assertIn('live CA acceptance remains outstanding', checklist)
        for repository in self.root.iterdir():
            self.assertFalse((repository / '.ai/ca-implementation.md').exists())
