# Outputs for MetalLB module

output "metallb_namespace" {
  value = kubernetes_namespace.metallb.metadata[0].name
  description = "MetalLB namespace"
}

output "metallb_configmap_name" {
  value = kubernetes_config_map.metallb_config.metadata[0].name
  description = "MetalLB ConfigMap name"
}
