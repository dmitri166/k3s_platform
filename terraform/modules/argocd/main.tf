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
    random = {
      source  = "hashicorp/random"
      version = "~> 3.5"
    }
  }
}

# Create namespace
resource "kubernetes_namespace" "argocd" {
  metadata {
    name = var.argocd_namespace
    labels = {
      "app.kubernetes.io/name" = "argocd"
      "app.kubernetes.io/part-of" = "talos-platform"
    }
  }
}

# Generate ArgoCD admin password
resource "random_password" "argocd_admin" {
  length  = 16
  special = true
}

# Create ArgoCD admin secret
resource "kubernetes_secret" "argocd_admin" {
  metadata {
    name      = "argocd-admin-password"
    namespace = kubernetes_namespace.argocd.metadata[0].name
  }

  data = {
    password = random_password.argocd_admin.result
  }

  type = "Opaque"
}

# Install ArgoCD via Helm
resource "helm_release" "argocd" {
  name       = "argocd"
  repository = var.argocd_helm_config.repository
  chart      = var.argocd_helm_config.chart
  version    = var.argocd_helm_config.version
  namespace  = kubernetes_namespace.argocd.metadata[0].name
  
  values = [
    yamlencode(merge(var.argocd_values, {
      server = {
        service = {
          type = "LoadBalancer"
          loadBalancerIP = "192.168.1.240"
          ports = {
            http = 80
            https = 443
          }
          annotations = {
            "metallb.universe.tf/address-pool" = "default"
          }
        }
      }
    }))
  ]
  
  depends_on = [
    kubernetes_namespace.argocd,
    kubernetes_secret.argocd_admin
  ]
}

# Wait for ArgoCD to be ready
resource "null_resource" "argocd_ready" {
  depends_on = [
    helm_release.argocd
  ]
  
  provisioner "local-exec" {
    command = "kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=argocd-server -n ${var.argocd_namespace} --timeout=300s"
  }
}
