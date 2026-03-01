# Output values for Talos on-premises platform

output "cluster_name" {
  value       = local.cluster_name
  description = "Name of the Kubernetes cluster"
}

output "kubeconfig_path" {
  value       = local.kubeconfig_path
  description = "Path to the kubeconfig file"
}

output "talosconfig_path" {
  value       = local.talosconfig_path
  description = "Path to the talosconfig file"
}

output "control_plane_ips" {
  value = {
    for node in var.control_plane_nodes : node.key => node.value.ip
  }
  description = "IP addresses of control plane nodes"
}

output "worker_ips" {
  value = {
    for node in var.worker_nodes : node.key => node.value.ip
  }
  description = "IP addresses of worker nodes"
}

output "all_node_ips" {
  value = {
    for node in local.all_nodes : node.key => node.value.ip
  }
  description = "IP addresses of all nodes"
}

output "argocd_url" {
  value       = "http://192.168.1.240"
  description = "URL for ArgoCD web interface"
}

output "argocd_admin_password" {
  value     = random_password.argocd_admin.result
  sensitive = true
  description = "ArgoCD admin password"
}

output "ingress_url" {
  value       = "http://192.168.1.241"
  description = "URL for ingress services"
}

output "grafana_url" {
  value       = "http://192.168.1.242"
  description = "URL for Grafana dashboard"
}

output "prometheus_url" {
  value       = "http://192.168.1.243"
  description = "URL for Prometheus interface"
}

output "vault_url" {
  value       = "http://192.168.1.244"
  description = "URL for Vault interface"
}

output "metallb_ip_range" {
  value       = local.metallb_pool
  description = "IP range for MetalLB LoadBalancer services"
}

output "network_cidr" {
  value       = local.network_cidr
  description = "Network CIDR for the cluster"
}

output "talos_version" {
  value       = local.talos_version
  description = "Talos OS version deployed"
}

output "kubernetes_version" {
  value       = local.kubernetes_version
  description = "Kubernetes version deployed"
}
