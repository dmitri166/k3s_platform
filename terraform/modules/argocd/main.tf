# ArgoCD module for GitOps deployment

terraform {
  required_providers {
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.11"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.23"
    }
  }
}

# Create namespace
resource "kubernetes_namespace" "argocd" {
  metadata {
    name = var.argocd_namespace
    labels = {
      "app.kubernetes.io/name"    = "argocd"
      "app.kubernetes.io/part-of" = "k3s-platform"
    }
  }
}

# Install ArgoCD via Helm
resource "helm_release" "argocd" {
  name       = "argocd"
  repository = var.argocd_helm_config.repository
  chart      = var.argocd_helm_config.chart
  version    = var.argocd_helm_config.version
  namespace  = kubernetes_namespace.argocd.metadata[0].name

  values = [yamlencode(var.argocd_values)]

  depends_on = [
    kubernetes_namespace.argocd
  ]
}
