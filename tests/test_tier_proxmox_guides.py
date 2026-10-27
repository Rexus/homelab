"""Proxmox 9.x reader path and template/failover correspondence."""

import yaml

from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM


class ProxmoxGuides(TierRepositoryTestCase):
    def test_ha_distinguishes_native_recovery_balancing_and_manual_setup(self):
        self.generate()
        for docs in (UPSTREAM / "docs", self.root / "verify-architecture/docs/auto-docs"):
            ha = (docs / "deployment/foundation/step-1b-cluster-ha.md").read_text()
            for term in ("Proxmox VE 9+", "9.2+ native HA", "fenced", "cold restart",
                         "HA-managed resources only", "does not create the host cluster",
                         "proxmox/failover.md", "reference/proxmox-ha.md", "proxmox/proxlb.md"):
                self.assertIn(term, ha)
            reference = (docs / "reference/proxmox-ha.md").read_text()
            for field in ("Max. Restart", "Max. Relocate", "Failback", "Auto-Rebalance",
                          "Node Affinity", "Resource Affinity", "Shutdown Policy",
                          "Scheduling Mode", "Rebalance on Start", "Automatic Rebalance",
                          "Imbalance Threshold", "Hold Duration", "Minimum Imbalance Improvement",
                          "Rebalancing Method", "Disarm"):
                self.assertIn(field, reference)
            alternative = (docs / "deployment/foundation/proxmox/proxlb.md").read_text()
            self.assertIn("plb_ignore_<purpose>", alternative)
            self.assertIn("does **not** enroll guests", alternative)
            self.assertIn("--dry-run", alternative)

    def test_failover_uses_existing_directory_hosts_not_an_extra_deployment(self):
        groups = yaml.safe_load((UPSTREAM / "tier-0/ansible/inventory/hosts.yml.example").read_text())["all"]["children"]
        names = set(groups["identity_primary"]["hosts"]) | set(groups["identity_replicas"]["hosts"])
        guide = (UPSTREAM / "docs/deployment/foundation/proxmox/failover.md").read_text()
        for name in names:
            self.assertIn(name, guide)
        self.assertEqual(guide.count("```mermaid"), 2)
        self.assertIn("operator-selected example", guide)
        self.assertIn("same VMID and disks", guide)
        self.assertIn("third waits", guide)
        self.assertIn("not a second", guide)

    def test_common_import_path_and_talos_exceptions_are_explicit(self):
        self.generate()
        docs = self.root / "verify-architecture/docs/auto-docs"
        guide = (docs / "deployment/foundation/proxmox/templates.md").read_text()
        for term in ("AlmaLinux", "Rocky Linux", "Cloud server", "NoCloud", "amd64",
                     "siderolabs/qemu-guest-agent", "UEFI only", "Pre-Enroll keys unchecked",
                     "Ballooning unchecked", "`.raw` only", "not the compressed archive",
                     "VirtIO SCSI", "virtio-scsi-pci", "Convert to template", "unbooted",
                     "CloudInit Drive", "static IPv4/CIDR", "leave **User, Password, SSH public keys, DNS"):
            self.assertIn(term, guide)
        for old in ("enterprise-linux-template.md", "talos-template.md"):
            self.assertFalse((docs / "deployment/foundation/procedures" / old).exists())
        self.assertIn("## Cluster handoff", guide)
        self.assertFalse((docs / "deployment/foundation/procedures").exists())
        cluster = (docs / "deployment/stage-4-kubernetes/procedures/talos-terraform.md").read_text()
        self.assertIn("vm_firmware", cluster)
        self.assertIn("not a firmware", cluster)
