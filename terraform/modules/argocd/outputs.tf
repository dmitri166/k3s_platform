# Outputs for ArgoCD module

output "argocd_namespace" {
  value = kubernetes_namespace.argocd.metadata[0].name
  description = "ArgoCD namespace"
}

output "argocd_server_url" {
  value = "http://192.168.1.240"
  description = "ArgoCD server URL"
}

output "argocd_admin_password" {
  value     = random_password.argocd_admin.result
  sensitive = true
  description = "ArgoCD admin password"
}
