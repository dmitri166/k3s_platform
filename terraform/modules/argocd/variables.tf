# Variables for ArgoCD module

variable "argocd_namespace" {
  type        = string
  default     = "argocd"
  description = "ArgoCD namespace"
}

variable "argocd_helm_config" {
  type = object({
    repository = string
    chart      = string
    version    = string
  })
  description = "ArgoCD Helm chart configuration"
}

variable "argocd_values" {
  type        = any
  default     = {}
  description = "ArgoCD Helm values"
}
