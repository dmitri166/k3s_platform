# Outputs for ArgoCD Applications module

output "deployed_applications" {
  value = {
    for app in var.applications : app.key => app.value
  }
  description = "List of deployed applications"
}
