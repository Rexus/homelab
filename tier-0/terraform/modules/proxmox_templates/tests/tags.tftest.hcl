mock_provider "proxmox" {}

variables {
  images = { for key, profile in {
    alma   = { family = "redhat", distribution = "alma", release = "10.2-20261012", vm_id = 9100 }
    rocky  = { family = "redhat", distribution = "rocky", release = "10.2-20260525", vm_id = 9101 }
    rhel   = { family = "redhat", distribution = "rhel", release = "10.2", vm_id = 9102 }
    debian = { family = "debian", distribution = "debian", release = "12.9-20250115", vm_id = 9103 }
    talos  = { family = "talos", distribution = "talos", release = "v1.14.5", vm_id = 9104 }
    fedora = { family = "redhat", distribution = "fedora", release = "42.1", vm_id = 9105 }
    ubuntu = { family = "debian", distribution = "ubuntu", release = "24.04-20250115", vm_id = 9106 }
    } : key => merge(profile, {
      name               = "${key}-fixture"
      node_name          = "pve01"
      datastore_id       = "local-lvm"
      image_datastore_id = "local"
      image_path         = abspath("tests/fixtures/template-image.${key == "talos" ? "raw" : "qcow2"}")
      sha256             = filesha256("tests/fixtures/template-image.${key == "talos" ? "raw" : "qcow2"}")
      schematic_id       = key == "talos" ? sha256("test schematic") : null
      cloud_init_drive   = true
      tags               = ["test", "test"]
    })
  }
}

run "reusable_image_tags_match_configured_profiles" {
  command = plan
  assert {
    condition = alltrue([for key in ["alma", "rocky", "rhel"] :
      toset(proxmox_virtual_environment_vm.template[key].tags) == toset([
        "el10", key, "x86-64-v3", "cloud-init", "test"
      ])
    ])
    error_message = "Enterprise Linux needs one el10 track plus distribution, CPU, CloudInit and custom tags, without redundant versions or ownership."
  }
  assert {
    condition = alltrue([for key, track in { debian = "debian12", talos = "talos1" } :
      toset(proxmox_virtual_environment_vm.template[key].tags) == toset([
        track, key, "x86-64-v3", "cloud-init", "test"
      ])
    ])
    error_message = "Debian and v-prefixed Talos releases must produce their actual major track."
  }
  assert {
    condition = alltrue([for key, vm in proxmox_virtual_environment_vm.template :
      output.catalog[key].tags == vm.tags &&
      !contains(vm.tags, "x86_64") && contains(vm.tags, lower(vm.cpu[0].type)) &&
      !contains(vm.tags, "template") && !contains(vm.tags, "tier-0") &&
      length(vm.tags) == length(distinct(vm.tags))
    ])
    error_message = "Candidate tags must match configured guests, remain unique and omit template status/tier ownership."
  }
  assert {
    condition = (
      contains(proxmox_virtual_environment_vm.template["fedora"].tags, "fedora42") &&
      !contains(proxmox_virtual_environment_vm.template["fedora"].tags, "el42") &&
      !contains(proxmox_virtual_environment_vm.template["fedora"].tags, "redhat42") &&
      contains(proxmox_virtual_environment_vm.template["ubuntu"].tags, "ubuntu24") &&
      !contains(proxmox_virtual_environment_vm.template["ubuntu"].tags, "debian24")
    )
    error_message = "A derivative's release must never be presented as its parent's release."
  }
}

run "cpu_and_cloudinit_tags_follow_actual_settings" {
  command = plan
  variables {
    images = { for key, image in var.images : key => merge(image, { cpu_type = "host", cloud_init_drive = false }) }
  }
  assert {
    condition = alltrue([for vm in proxmox_virtual_environment_vm.template :
      contains(vm.tags, "host") && !contains(vm.tags, "x86-64-v3") && !contains(vm.tags, "x86_64") &&
      !contains(vm.tags, "cloud-init") && length(vm.initialization) == 0
    ])
    error_message = "Tags must follow configured CPU/CloudInit changes without inventing detected host capabilities."
  }
}

run "legacy_distribution_as_family_remains_compatible" {
  command = plan
  variables {
    images = { for key, image in var.images : key => merge(image, {
      family       = contains(["alma", "rocky"], key) ? key : image.family
      distribution = contains(["alma", "rocky"], key) ? null : image.distribution
    }) }
  }
  assert {
    condition = alltrue([for key in ["alma", "rocky"] :
      contains(proxmox_virtual_environment_vm.template[key].tags, "el10") &&
      contains(proxmox_virtual_environment_vm.template[key].tags, key)
    ])
    error_message = "Legacy family: alma/rocky inputs must keep their Enterprise Linux track."
  }
}
