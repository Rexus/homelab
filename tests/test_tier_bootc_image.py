"""Native bootc image arguments, input/output guards and publisher handoff (no live build)."""

import base64
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

import jinja2
import yaml


UPSTREAM = Path(__file__).resolve().parents[1]
ROLE = UPSTREAM / "tier-0/ansible/roles/immutable_template"
DEFAULTS = yaml.safe_load((ROLE / "defaults/main.yml").read_text())
NATIVE = os.name != "nt" and bool(shutil.which("ansible-playbook"))
DIGEST = "@sha256:" + "0" * 64  # Test syntax only; never pulled or deployed.


def inputs(directory):
    return dict(
        ansible_os_family="RedHat", ansible_architecture="x86_64", ansible_user="automation",
        immutable_template_mode="image", immutable_template_image_builder_accepted=True,
        immutable_template_image_sources_approved=True, immutable_template_image_revision="test-1",
        immutable_template_bootc_image="registry.lab.test/platform/bootc" + DIGEST,
        immutable_template_image_builder_image="registry.redhat.io/rhel10/bootc-image-builder" + DIGEST,
        immutable_template_image_artifact_dir=str(directory), immutable_template_image_publication_key="bootc-test-1",
        immutable_template_image_publication={
            "family": "redhat", "distribution": "rhel", "release": "10.1-build-1", "vm_id": 9250,
            "name": "bootc-test-1", "image_datastore_id": "local", "storage_class": "shared",
            "bios": "ovmf", "machine": "q35", "cloud_init_drive": True, "qemu_agent": True,
            "disk_size_gb": 40,
        },
    )


class BootcImage(unittest.TestCase):
    def run_play(self, variables, tasks):
        with tempfile.TemporaryDirectory(prefix="homelab-bootc-test-") as name:
            directory = Path(name)
            playbook = directory / "verify.yml"
            playbook.write_text(yaml.safe_dump([{
                "hosts": "localhost", "connection": "local", "gather_facts": False,
                "vars": dict(DEFAULTS, ansible_python_interpreter="{{ ansible_playbook_python }}"), "tasks": tasks,
            }]))
            fixture = directory / "inputs.json"
            fixture.write_text(json.dumps(variables))
            return subprocess.run(
                ["ansible-playbook", "-i", "localhost,", str(playbook), "-e", "@" + str(fixture)],
                cwd=UPSTREAM / "tier-0/ansible", capture_output=True, text=True,
                env=dict(os.environ, ANSIBLE_CONFIG=str(UPSTREAM / "tier-0/ansible/ansible.cfg"),
                         ANSIBLE_ROLES_PATH=str(UPSTREAM / "tier-0/ansible/roles"),
                         ANSIBLE_LOCAL_TEMP=str(directory / "local")),
            )

    def test_native_builder_is_separate_from_existing_host_switch_and_cleanup(self):
        main = yaml.safe_load((ROLE / "tasks/main.yml").read_text())
        self.assertEqual(main[1]["when"], "immutable_template_mode == 'image'")
        self.assertEqual(main[2]["when"], "immutable_template_mode == 'host'")
        text = "\n".join(path.read_text() for path in (ROLE / "tasks").glob("bootc-image*.yml"))
        self.assertNotIn("install to-existing-root", text)
        self.assertNotIn("ansible.builtin.shell", text)
        self.assertNotIn("recurse: true", text)
        self.assertIn("ansible.builtin.fetch", text)
        self.assertIn("containers.podman.podman_image", text)
        self.assertIn("checksum_algorithm: sha256", text)
        self.assertEqual(DEFAULTS["immutable_template_mode"], "host")
        example = yaml.safe_load((UPSTREAM / "tier-0/ansible/group_vars/immutable_template.yml.example").read_text())
        self.assertEqual(example["immutable_template_mode"], "image")
        self.assertFalse(example["immutable_template_apply_bootc"])
        self.assertFalse(example["immutable_template_image_builder_accepted"])

    def test_publication_uses_the_existing_terraform_disk_contract_without_secrets(self):
        environment = jinja2.Environment(undefined=jinja2.StrictUndefined)
        environment.filters["to_nice_yaml"] = yaml.safe_dump
        environment.filters["combine"] = lambda first, second: dict(first, **second)
        variables = inputs(Path("/private/artifacts"))
        variables.update(immutable_template_image_controller_dir="/private/artifacts/builder/test-1",
                         immutable_template_image_fetched={"stat": {"checksum": "a" * 64}},
                         immutable_template_registry_auth_src="PRIVATE-CREDENTIAL-SENTINEL")
        rendered = environment.from_string((ROLE / "templates/bootc-image-publication.yml.j2").read_text()).render(**variables)
        publication = yaml.safe_load(rendered)["templates"]["bootc-test-1"]
        self.assertEqual(publication["image_path"], "/private/artifacts/builder/test-1/disk.qcow2")
        self.assertEqual(publication["sha256"], "a" * 64)
        self.assertNotIn("PRIVATE-CREDENTIAL-SENTINEL", rendered)
        schema = (UPSTREAM / "tier-0/terraform/modules/proxmox_templates/variables.tf").read_text()
        self.assertIn("image_path", schema)
        self.assertIn("sha256", schema)

    @unittest.skipUnless(NATIVE, "Requires native Ansible on Linux/WSL")
    def test_rejects_unapproved_images_unsafe_revisions_and_root_conversion(self):
        overrides = [
            {"ansible_os_family": "Debian"}, {"ansible_architecture": "aarch64"},
            {"immutable_template_image_builder_accepted": False},
            {"immutable_template_image_sources_approved": False},
            {"immutable_template_bootc_image": "registry.lab.test/bootc:latest"},
            {"immutable_template_image_builder_image": "registry.lab.test/builder:latest"},
            {"immutable_template_image_revision": "../outside"}, {"immutable_template_image_rootfs": "auto"},
            {"immutable_template_apply_bootc": True}, {"immutable_template_prepare_for_template": True},
            {"immutable_template_reboot_after_switch": True}, {"immutable_template_image_artifact_dir": "/"},
        ]
        task = {"ansible.builtin.import_role": {"name": "immutable_template", "tasks_from": "preflight"}}
        with tempfile.TemporaryDirectory(prefix="homelab-bootc-artifacts-") as name:
            for override in ({}, *overrides):
                with self.subTest(override=override):
                    result = self.run_play(dict(inputs(Path(name)), **override), [task])
                    self.assertEqual(result.returncode == 0, not override, result.stdout + result.stderr)
                    if override:
                        self.assertIn('"evaluated_to": false', result.stdout, result.stdout + result.stderr)
            self.assertEqual(list(Path(name).iterdir()), [])

    @unittest.skipUnless(NATIVE, "Requires native Ansible on Linux/WSL")
    def test_native_container_arguments_render_to_scoped_mounts_and_real_qcow2_command(self):
        build = yaml.safe_load((ROLE / "tasks/bootc-image-build.yml").read_text())
        block = next(task["block"] for task in build if "block" in task)
        container = next(task["containers.podman.podman_container"] for task in block
                         if "containers.podman.podman_container" in task)
        with tempfile.TemporaryDirectory(prefix="homelab-bootc-render-") as name:
            path = Path(name) / "container.json"
            variables = inputs(Path(name))
            variables.update(immutable_template_image_workdir="/var/lib/bootc-image-builder/test-1", contract=container)
            result = self.run_play(variables, [{
                "ansible.builtin.copy": {"content": "{{ contract | to_nice_json }}", "dest": str(path), "mode": "0600"},
            }])
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            rendered = json.loads(path.read_text())
            self.assertTrue(rendered["privileged"])
            self.assertFalse(rendered["detach"])
            self.assertEqual(rendered["pull"], "never")
            self.assertEqual(rendered["command"], ["--type", "qcow2", "--rootfs", "xfs", "--config", "/config.json",
                                                   variables["immutable_template_bootc_image"]])
            self.assertEqual(rendered["volume"], [
                "/var/lib/containers/storage:/var/lib/containers/storage:rw",
                "/var/lib/bootc-image-builder/test-1/config.json:/config.json:ro",
                "/var/lib/bootc-image-builder/test-1/output:/output:rw",
            ])
            info = subprocess.run(["ansible-doc", "-j", "containers.podman.podman_container"],
                                  capture_output=True, text=True)
            self.assertEqual(info.returncode, 0, info.stderr)
            options = json.loads(info.stdout)["containers.podman.podman_container"]["doc"]["options"]
            supported = set(options) | {alias for option in options.values() for alias in option.get("aliases", [])}
            self.assertFalse(set(rendered) - supported)

    @unittest.skipUnless(NATIVE, "Requires native Ansible on Linux/WSL")
    def test_ownership_and_artifact_guards_reject_foreign_partial_and_changed_output(self):
        workspace = yaml.safe_load((ROLE / "tasks/bootc-image-workspace.yml").read_text())
        ownership = copy.deepcopy(workspace[1])
        revision = copy.deepcopy(workspace[2])
        changed = copy.deepcopy(workspace[4])
        paths = [{"stat": {"exists": False}, "item": str(i)} for i in range(7)]
        cases = [
            (ownership, {"immutable_template_image_paths": {"results": paths}}, True),
            (ownership, {"immutable_template_image_paths": {"results": [
                {"stat": {"exists": True, "islnk": True, "uid": 0}, "item": "symlink"}]}}, False),
            (ownership, {"immutable_template_image_paths": {"results": [
                {"stat": {"exists": True, "islnk": False, "uid": 1000}, "item": "foreign"}]}}, False),
        ]
        for index in (1, 5):
            unsafe = copy.deepcopy(paths)
            unsafe[index]["stat"]["exists"] = True
            cases.append((revision, {"immutable_template_image_paths": {"results": unsafe}}, False))
        for previous in ({"source": "same"}, {"source": "different"}):
            cases.append((changed, {
                "immutable_template_image_request": {"source": "same"},
                "immutable_template_image_previous_request": {
                    "content": base64.b64encode(json.dumps(previous).encode()).decode(),
                },
            }, previous["source"] == "same"))
        build = yaml.safe_load((ROLE / "tasks/bootc-image-build.yml").read_text())
        hash_guard = next(task for task in build if task["name"] == "Reject changed or corrupted completed artifacts")
        for checksum in ("a" * 64, "b" * 64):
            cases.append((hash_guard, {
                "immutable_template_image_disk": {"stat": {"checksum": checksum}},
                "immutable_template_image_previous_result": {
                    "content": base64.b64encode(json.dumps({"sha256": "a" * 64}).encode()).decode(),
                },
            }, checksum == "a" * 64))
        disk_guard = next(task for task in build if task["name"].startswith("Require a standalone qcow2"))
        for override, accepted in (({}, True), ({"format": "raw"}, False),
                                   ({"backing-filename": "/foreign/base.qcow2"}, False),
                                   ({"format-specific": {"data": {"data-file": "/foreign/data"}}}, False),
                                   ({"virtual-size": 41 * 1073741824}, False)):
            cases.append((disk_guard, {
                "immutable_template_image_info": {
                    "stdout": json.dumps(dict({"format": "qcow2", "virtual-size": 1073741824}, **override)),
                },
                "immutable_template_image_publication": {"disk_size_gb": 40},
            }, accepted))
        host = yaml.safe_load((ROLE / "tasks/host.yml").read_text())
        native_guard = next(task for task in host if task["name"].startswith("Require a bootc-native"))
        for booted in (None, {"image": {"image": "registry.lab.test/bootc" + DIGEST}}):
            cases.append((native_guard, {"immutable_template_bootc_status": {
                "rc": 0, "stdout": json.dumps({"status": {"booted": booted}}),
            }}, booted is not None))
        tasks = []
        for task, variables, accepted in cases:
            task = copy.deepcopy(task)
            task.pop("when", None)
            task["vars"] = dict(task.get("vars", {}), **variables)
            if accepted:
                tasks.append(task)
            else:
                tasks.append({"block": [task, {"ansible.builtin.fail": {"msg": "UNSAFE-GUARD-ACCEPTED"}}],
                              "rescue": [{"ansible.builtin.assert": {"that": [
                                  "ansible_failed_result.msg != 'UNSAFE-GUARD-ACCEPTED'",
                              ]}}]})
        result = self.run_play({}, tasks)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    @unittest.skipUnless(NATIVE, "Requires native Ansible and declared collections")
    def test_deployment_entrypoints_parse_with_native_modules(self):
        with tempfile.TemporaryDirectory(prefix="homelab-bootc-syntax-") as name:
            fixture = Path(name) / "image-branch.yml"
            fixture.write_text(yaml.safe_dump([{"hosts": "localhost", "gather_facts": False, "tasks": [
                {"ansible.builtin.import_role": {"name": "immutable_template", "tasks_from": "bootc-image"}},
            ]}]))
            for recipe in ("playbooks/deployment/immutable-template.yml", "playbooks/deployment/bootc-image.yml", str(fixture)):
                result = subprocess.run(
                    ["ansible-playbook", "-i", "localhost,", recipe, "--syntax-check"],
                    cwd=UPSTREAM / "tier-0/ansible", capture_output=True, text=True,
                    env=dict(os.environ, ANSIBLE_CONFIG=str(UPSTREAM / "tier-0/ansible/ansible.cfg")),
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
