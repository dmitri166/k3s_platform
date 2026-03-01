# Variables for ArgoCD Applications module

variable "kubeconfig" {
  type        = string
  description = "Kubernetes kubeconfig content"
}

variable "applications" {
  type        = map(any)
  description = "Map of ArgoCD applications to deploy"
}
