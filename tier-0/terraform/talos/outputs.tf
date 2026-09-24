data "talos_client_configuration" "cluster" {
  cluster_name         = var.cluster.name
  client_configuration = talos_machine_secrets.cluster.client_configuration
  endpoints            = [for name in sort(tolist(local.control_planes)) : local.host_ips[name]]
  nodes                = [for name in sort(tolist(local.control_planes)) : local.host_ips[name]]
}

resource "talos_cluster_kubeconfig" "cluster" {
  depends_on           = [talos_machine_bootstrap.cluster]
  node                 = local.host_ips[var.cluster.bootstrap_node]
  client_configuration = talos_machine_secrets.cluster.client_configuration
}

output "talosconfig" {
  description = "Protect as a cluster administrator credential; use the credentials command, not CI logs."
  value       = data.talos_client_configuration.cluster.talos_config
  sensitive   = true
}

output "kubeconfig" {
  description = "Bootstrap Kubernetes credential; normal access must later be scoped."
  value       = talos_cluster_kubeconfig.cluster.kubeconfig_raw
  sensitive   = true
}

output "machine_configurations" {
  description = "Per-node recovery configurations, including secrets."
  value       = { for name, config in data.talos_machine_configuration.node : name => config.machine_configuration }
  sensitive   = true
}

output "nodes" {
  description = "Inventory-derived endpoints and observed Proxmox placement."
  value = { for name, vm in proxmox_virtual_environment_vm.node : name => {
    vm_id = vm.vm_id, node_name = vm.node_name, ip = local.machines[name].ip, role = local.machines[name].role
  } }
}
