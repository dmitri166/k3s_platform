# Output values for K3s on-premises platform

output "cluster_name" {
  value       = local.cluster_name
  description = "Name of the Kubernetes cluster"
}

output "kubeconfig_path" {
  value       = local.kubeconfig_path
  description = "Path to the kubeconfig file"
}

output "control_plane_ips" {
  value = {
    for key, node in var.control_plane_nodes : key => node.ip
  }
  description = "IP addresses of control plane nodes"
}

output "worker_ips" {
  value = {
    for key, node in var.worker_nodes : key => node.ip
  }
  description = "IP addresses of worker nodes"
}

output "all_node_ips" {
  value = {
    for key, node in local.all_nodes : key => node.ip
  }
  description = "IP addresses of all nodes"
}

output "argocd_url" {
  value       = "http://192.168.56.240"
  description = "URL for ArgoCD web interface"
}

output "argocd_initial_admin_password_command" {
  value       = module.argocd.argocd_initial_admin_password_command
  description = "Command to retrieve ArgoCD initial admin password"
}

output "ingress_url" {
  value       = "http://192.168.56.241"
  description = "URL for ingress services"
}

output "grafana_url" {
  value       = "http://192.168.56.242"
  description = "URL for Grafana dashboard"
}

output "prometheus_url" {
  value       = "http://192.168.56.243"
  description = "URL for Prometheus interface"
}

output "vault_url" {
  value       = "http://192.168.56.244"
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

output "kubernetes_version" {
  value       = local.kubernetes_version
  description = "Kubernetes version deployed"
}
