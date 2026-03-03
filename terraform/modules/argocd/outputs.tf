# Outputs for ArgoCD module

output "argocd_namespace" {
  value       = kubernetes_namespace.argocd.metadata[0].name
  description = "ArgoCD namespace"
}

output "argocd_server_url" {
  value       = "http://192.168.56.245"
  description = "ArgoCD server URL"
}

output "argocd_initial_admin_password_command" {
  value       = "kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 --decode"
  description = "Command to retrieve ArgoCD initial admin password"
}
