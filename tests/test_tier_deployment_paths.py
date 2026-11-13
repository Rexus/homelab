"""Prerequisites and deployable capabilities have distinct, navigable entry points."""

import re

from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM


class DeploymentPaths(TierRepositoryTestCase):
    def test_main_actions_keep_preparation_apply_and_acceptance_in_sequence(self):
        self.generate()
        # These contracts follow executable actions and their prerequisites rather
        # than forcing all capabilities into the former three-phase outline.
        required = {
            3: {2: 'init-local-files.sh --setup foundation', 3: 'terraform/deployments/foundation/terraform.tfvars',
                6: 'openxpki-bundle.yml', 7: 'deploy.sh foundation --terraform-only',
                9: 'deployment/openxpki.yml', 10: 'deployment/openxpki-key.yml',
                11: 'offline', 12: 'deployment/openxpki-certificates.yml', 14: 'recovery'},
            4: {2: 'init-local-files.sh --setup cluster-endpoint', 3: 'deploy.sh cluster-endpoint',
                5: 'terraform/deployments/kubernetes/terraform.tfvars',
                7: 'cluster_security_logging_action=render', 8: 'kubernetes-cluster.sh plan',
                9: 'kubernetes-cluster.sh apply', 10: 'kubernetes-cluster.sh credentials',
                12: 'cluster_platform_action=render', 13: 'cluster_platform_action=apply',
                14: 'cluster_security_logging_action=apply', 16: 'Flux',
                17: 'cluster_platform_action=render', 18: 'cluster_platform_action=apply',
                19: 'recovery'},
            5: {2: 'foundation.yml', 3: 'deploy.sh foundation --terraform-only',
                7: 'deploy.sh foundation --ansible-only', 8: 'offline',
                9: 'foundation_freeipa_external_phase: complete', 10: 'deploy.sh foundation --ansible-only',
                11: 'deploy.sh foundation --recipe maintenance', 13: 'control_applications_ldap_bind_dn',
                15: 'control_applications_action=render', 16: 'control_applications_action=apply',
                18: 'control_applications_action=render', 19: 'control_applications_action=apply',
                20: 'restor', 21: 'kubernetes-sso.md', 22: 'kubernetes-cli-access.md', 23: 'X509'},
            6: {3: 'control_applications_secrets.yml', 4: 'control_applications_action=render',
                5: 'control_applications_action=apply', 6: 'unseal', 9: 'maintenance/control-backup.yml',
                12: 'mon-1', 18: 'deployment/netbox-audit.yml',
                20: 'infrastructure_monitoring_action=render', 21: 'recovery'},
            7: {2: 'delivery_platform.yml', 3: 'Secret', 4: 'delivery_platform_action=render',
                6: 'delivery_platform_action=apply', 7: 'recovery', 8: 'Harbor',
                9: 'delivery_platform_action=render', 10: 'delivery_platform_action=apply',
                11: 'recovery', 12: 'edge-proxy.md'},
            8: {3: 'observability_platform.yml', 4: 'observability_platform_secrets.yml',
                5: 'SSO', 6: 'backup', 7: 'observability_action=render',
                8: 'observability_action=apply', 9: 'NAS',
                10: 'observability_action=render', 11: 'observability_action=apply',
                13: 'step-13-infrastructure-monitoring.md', 15: 'recovery'},
            9: {2: 'init-local-files.sh --setup development-data', 3: 'terraform.tfvars',
                4: 'deploy.sh development-data --terraform-only',
                6: 'development_data_tls', 7: 'development_data_action=render',
                8: 'development_data_action=apply', 10: 'Secret',
                11: 'development_platform_action=render', 12: 'development_platform_action=apply',
                13: 'backup-utility', 14: 'step-14a-kubernetes-runners.md',
                16: 'direct-CI trust', 17: 'terraform/deployments/ci-auth/terraform.tfvars',
                18: 'deploy.sh infrastructure-runner', 19: 'Vault',
                20: 'deployment/infrastructure-handover.yml', 21: 'recovery'},
            10: {1: 'approved', 2: 'deploy.sh lab', 3: 'step-3a-application.md',
                 4: 'step-4b-public-https.md', 5: 'step-5b-telemetry.md', 6: 'restore'},
        }
        for docs in (UPSTREAM / 'docs', self.root / 'verify-architecture/docs/auto-docs'):
            for stage, markers in required.items():
                path = next((docs / '03-deployment').glob(f'stage-{stage}-*/README.md'))
                content = path.read_text(encoding='utf-8')
                actions = {int(match[1]): match[2] for match in re.finditer(
                    r'(?ms)^## Step (\d+):[^\n]*\n(.*?)(?=^## |\Z)', content)}
                for step, marker in markers.items():
                    self.assertIn(marker.lower(), actions[step].lower(), f'{path.parent.name}, action {step}')

    def test_capability_names_have_unique_numbers_and_federation_belongs_to_identity(self):
        self.generate()
        expected = ["stage-1-software-intake", "stage-2-logging", "stage-3-trust", "stage-4-kubernetes",
                    "stage-5-identity", "stage-6-secrets",
                    "stage-7-delivery", "stage-8-observability", "stage-9-development", "stage-10-lab-environments"]
        for docs in (UPSTREAM / "docs", self.root / "verify-architecture/docs/auto-docs"):
            root = docs / "03-deployment"
            directories = sorted((path.name for path in root.glob("stage-*") if path.is_dir()),
                                 key=lambda name: int(name.split("-")[1]))
            self.assertEqual(directories, expected)
            numbers = [int(name.split("-")[1]) for name in directories]
            self.assertEqual(numbers, list(range(1, 11)))
            identity = (root / "stage-5-identity/README.md").read_text()
            secrets = (root / "stage-6-secrets/README.md").read_text()
            self.assertTrue(identity.startswith("# Stage 5: Identity\n"))
            self.assertTrue(secrets.startswith("# Stage 6: Secrets\n"))
            federation = identity.split("## Step 12: Select the existing cluster and identity-provider inputs", 1)[1]
            for term in ("control-applications.yml", "control_applications_keycloak_realm",
                         "control_applications_ldap_bind_dn", "read-only FreeIPA federation", "**IaC:**"):
                self.assertIn(term, federation)
            self.assertIn("## Step 1: Select Vault placement and seal", secrets)
            self.assertIn("Keycloak[\"Existing Keycloak / IdP\"]", secrets)
            added = re.search(r'subgraph Added\[.*?\n        end', secrets, re.DOTALL)[0]
            self.assertNotIn("Keycloak", added)
            self.assertIn("step-1b-vault-vm.md", secrets)
            self.assertIn("step-1c-seal-integration.md", secrets)
            index = (root / "README.md").read_text()
            self.assertIn('Runtime["4. Kubernetes<br/>', index)
            self.assertIn('Identity["5. Identity<br/>', index)
            self.assertIn('Control["6. Secrets<br/>', index)

    def test_foundation_is_unnumbered_and_intake_precedes_logging(self):
        self.generate()
        for docs in (UPSTREAM / "docs", self.root / "verify-architecture/docs/auto-docs"):
            root = docs / "03-deployment"
            foundation = (root / "foundation/README.md").read_text()
            self.assertTrue(foundation.startswith("# Foundation and prerequisites"))
            self.assertIn("not a numbered capability stage", foundation)
            self.assertNotIn("## Step 4: Establish protected logging", foundation)
            self.assertIn("stage-2-logging/README.md", foundation)
            stages = sorted(root.glob("stage-*/README.md"), key=lambda path: int(path.parent.name.split("-")[1]))
            self.assertEqual(stages[0].parent.name, "stage-1-software-intake")
            self.assertFalse((root / "stage-1-foundation").exists())
            expected_steps = {
                "stage-2-logging/README.md": [str(number) for number in range(1, 17)],
                "stage-6-secrets/procedures/independent-monitoring.md": ["1", "2", "3"],
                "stage-8-observability/README.md": [str(number) for number in range(1, 16)],
                "stage-10-lab-environments/step-5b-telemetry.md": [str(number) for number in range(1, 9)],
            }
            for relative, expected in expected_steps.items():
                content = (root / relative).read_text()
                steps = re.findall(r"(?m)^## Step (\d+):", content)
                self.assertEqual(steps, expected, relative)
                sections = re.split(r"(?m)^## Step \d+:", content)[1:]
                self.assertIn("```mermaid", content, relative)
                # A step can refer to a result figure introduced earlier; action
                # numbering must not force a duplicate diagram for the same topology.
                if relative not in ("stage-2-logging/README.md", "stage-8-observability/README.md",
                                    "stage-10-lab-environments/step-5b-telemetry.md"):
                    for section in sections:
                        if "```mermaid" not in section:
                            self.assertRegex(section, r"\]\(#figure-[^)]+\)", relative)
                self.assertRegex(content, r"\*\*Working repositor(?:y|ies):\*\*", relative)
                self.assertIn("**Prerequisites:**", content, relative)
            logging = stages[1].read_text()
            headings = list(re.finditer(r"(?m)^## Step (\d+):", logging))
            actions = {int(heading[1]): logging[heading.end():
                       headings[index + 1].start() if index + 1 < len(headings) else len(logging)]
                       for index, heading in enumerate(headings)}
            executable = {number: "\n".join(re.findall(r"```bash\n(.*?)```", action, re.S))
                          for number, action in actions.items()}
            required_commands = {
                1: "bash scripts/init-local-files.sh --setup syslog",
                3: "bash scripts/deploy.sh syslog --terraform-only",
                4: "--ansible-only --playbook deployment/logging-storage.yml",
                6: "ansible/playbooks/deployment/logging-receiver-request.yml",
                7: "log_forwarder_mode=prepare",
                8: "community.crypto.openssl_csr_info",
                9: "ansible/playbooks/deployment/logging-authority.yml",
                11: "bash scripts/deploy.sh syslog --ansible-only",
                12: "ansible/playbooks/deployment/logging-producers.yml",
            }
            for number, command in required_commands.items():
                self.assertIn(command, executable[number], f"Logging action {number}")
            for field in ("terraform/deployments/syslog/terraform.tfvars", "syslog_ng_data_device"):
                self.assertIn(field, actions[2])
            self.assertIn("syslog_ng_sources:", actions[10])
            self.assertIn("SYSLOG_NG_TLS_CERT_FILE", executable[10])
            self.assertNotIn("log_forwarder_mode=prepare", executable[12])
            self.assertIn("logging-acceptance-event-001", executable[12])
            self.assertNotIn("logging-authority.yml", "\n".join(executable[n] for n in range(1, 9)))
            self.assertNotRegex("\n".join(executable[n] for n in range(1, 11)),
                                r"(?m)^bash scripts/deploy\.sh syslog --ansible-only\s*$")
            authority_choices = re.split(r"(?m)^### 9[ab][.:] ", actions[9])
            self.assertEqual(len(authority_choices), 3)
            self.assertIn("logging_authority_initialize=true", authority_choices[1])
            self.assertNotIn("logging_authority_initialize=true", authority_choices[2])
            self.assertIn("logging-authority.yml", authority_choices[2])
            self.assertEqual(re.findall(r"(?m)^### (\d+[a-z])[.:] ", logging), ["9a", "9b"])
            self.assertEqual(re.findall(r"(?m)^\| \*\*(\d+[a-z]):", logging),
                             ["14a", "14b", "15a", "15b"])
            self.assertEqual(len(re.findall(r"```mermaid\n", logging)), 3)
            self.assertIn("baseline", actions[4])
            self.assertIn("sources.md", logging)
            self.assertIn("step-15a-nas-archive.md", logging)
            self.assertIn("declared durability limits", logging)

    def test_every_runnable_root_has_a_capability_and_walkthrough(self):
        self.generate()
        for docs, collection, prefix in (
            (UPSTREAM / "docs", UPSTREAM, ""),
            (self.root / "verify-architecture/docs/auto-docs", self.root, "verify-"),
        ):
            index = (docs / "03-deployment/README.md").read_text()
            capability_map = index.split("## IaC capability map\n", 1)[1].split("## Repository locations\n", 1)[0]
            entries = re.findall(r"(?m)^\| Tier ([012]) \| `([^`]+)` \|", capability_map)
            expected = set()
            for number in range(3):
                tier = collection / f"{prefix}tier-{number}"
                setups = set((tier / ".deployment-setups").read_text().splitlines()) | {"kubernetes"}
                if number == 0:
                    setups.update({"templates", "ci-auth"})
                expected.update((str(number), setup) for setup in setups)
                for setup in setups:
                    self.assertTrue((tier / "terraform/deployments" / setup / "main.tf").is_file())
            self.assertEqual(set(entries), expected)
            self.assertEqual(len(entries), len(expected))
            self.assertRegex(
                capability_map,
                r"(?m)^\| Tier 1 \| `intake` \| Stage 3[^\n]+"
                r"\(stage-3-trust/step-15b-verified-intake\.md\) \|$",
            )
            self.assertIn("never rename state roots", index)
            support = (docs / "08-reference/implementation-support.md").read_text()
            detailed = support.split("## Detailed coverage", 1)[1]
            row = next(line for line in detailed.splitlines() if "| Verified repository/artifact supply |" in line)
            self.assertRegex(row, r"^\| 3\b", "Reference coverage must place verified intake after trust/logging")

    def test_kubernetes_is_a_complete_reader_path_before_identity_consumers(self):
        self.generate()
        for docs in (UPSTREAM / "docs", self.root / "verify-architecture/docs/auto-docs"):
            deployment = docs / "03-deployment"
            cluster = (deployment / "stage-4-kubernetes/README.md").read_text()
            identity = (deployment / "stage-5-identity/README.md").read_text()
            self.assertEqual(re.findall(r"(?m)^## Step (\d+):", cluster),
                             [str(number) for number in range(1, 20)])
            implementation = (deployment / "stage-4-kubernetes/procedures/talos-terraform.md").read_text()
            self.assertIn("procedures/talos-terraform.md", cluster)
            for action in ("init", "plan", "apply", "credentials"):
                self.assertIn(f"bash scripts/kubernetes-cluster.sh {action}", implementation)
            for expected in ("independent DNS/time", "private", "API endpoint outside this cluster",
                             "cluster-security-logging.yml", "security-logging.md", "etcd",
                             "../stage-5-identity/README.md", "step-1b-existing-cluster.md"):
                self.assertIn(expected, cluster)
            self.assertEqual(re.findall(r"(?m)^## Step (\d+):", identity),
                             [str(number) for number in range(1, 24)])
            self.assertIn("../stage-4-kubernetes/README.md", identity)
            self.assertNotIn("## Step 2: Create the Kubernetes cluster", identity)
            for procedure in ("kubernetes.md", "talos-terraform.md"):
                self.assertTrue((deployment / "stage-4-kubernetes/procedures" / procedure).is_file())
                self.assertFalse((deployment / "stage-5-identity/procedures" / procedure).exists())
