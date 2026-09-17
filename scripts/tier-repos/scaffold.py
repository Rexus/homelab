"""Optional cluster bootstrap and workload skeletons, seeded once."""

import yaml

from generated_files import MARKER


def kustomization(writer, path, resources):
    content = {"apiVersion": "kustomize.config.k8s.io/v1beta1", "kind": "Kustomization",
               "resources": resources}
    writer.write(f"{path}/kustomization.yaml", f"# {MARKER}\n" + yaml.safe_dump(content, sort_keys=False),
                 owned=True)


def cluster_scaffold(writer, tier):
    if tier == "tier-2":
        for directory in ("environments/dev", "environments/prod", "workloads"):
            writer.write(f"{directory}/.gitkeep", "", owned=True)
        return
    root = f"clusters/{tier.replace('-', '')}"
    sections = {
        "infrastructure": ["cni", "ingress", "cert-manager", "external-secrets", "storage"],
        "databases": ["cloudnative-pg"],
        "applications": ["freeipa", "keycloak", "vault", "headlamp", "netbox"],
    } if tier == "tier-0" else {
        "infrastructure": ["ingress", "external-secrets", "policy", "storage"],
        "platform": ["source-control", "artifact-registry", "ci-runners", "observability", "cluster-management"],
    }
    kustomization(writer, root, list(sections))
    for section, components in sections.items():
        kustomization(writer, f"{root}/{section}", components)
        for component in components:
            kustomization(writer, f"{root}/{section}/{component}", [])
    if tier != "tier-0":
        return
    writer.write(f"{root}/flux-system/.gitkeep", "", owned=True)
    writer.write("bootstrap/talos/patches/.gitkeep", "", owned=True)
    placeholders = {
        "proxmox/main.tf": 'terraform {\n  required_version = ">= 1.6.0"\n}\n',
        "proxmox/backend.tf": 'terraform {\n  backend "local" {}\n}\n',
        "proxmox/network.tf": "# Define isolated custody networks here; no routed DMZ connection.\n",
        "proxmox/tier0-vms.tf": ("# Clone a tested Talos candidate from terraform/templates/ here.\n"
                                "# Keep machine config out of the template. See the Talos template guide.\n"),
        "talos/cluster.tf": "# Define Talos cluster bootstrap resources here.\n",
        "talos/machines.tf": "# Define Talos machines using tier-owned inventory and recovery inputs.\n",
    }
    for path, content in placeholders.items():
        writer.write(f"bootstrap/{path}", f"# {MARKER}\n\n{content}", owned=True)
