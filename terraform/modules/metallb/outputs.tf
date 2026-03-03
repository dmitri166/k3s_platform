# Outputs for MetalLB module

output "metallb_namespace" {
  value       = kubernetes_namespace.metallb.metadata[0].name
  description = "MetalLB namespace"
}

output "metallb_ipaddress_pool_name" {
  value       = kubernetes_manifest.metallb_ipaddress_pool.manifest.metadata.name
  description = "MetalLB IPAddressPool name"
}
