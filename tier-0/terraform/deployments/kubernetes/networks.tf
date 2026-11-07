# Read network metadata only; this tier still owns node IPs, resources and state.
# Reference: docs/reference/network-inputs.md#sdn-subnet-lookup
data "external" "sdn_network" {
  count   = try(var.bootstrap_network.sdn_vnet, null) == null ? 0 : 1
  program = ["python3", "${path.module}/../../../../shared/scripts/proxmox-sdn.py"]
  query   = { vnet = var.bootstrap_network.sdn_vnet }
}

locals {
  effective_bootstrap_network = var.bootstrap_network == null ? null : merge(
    var.bootstrap_network,
    try({
      prefix_length = tonumber(split("/", data.external.sdn_network[0].result.cidr_ipv4)[1])
      gateway       = data.external.sdn_network[0].result.gateway_ipv4
    }, {}),
  )
}
