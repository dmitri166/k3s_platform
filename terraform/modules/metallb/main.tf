# MetalLB module for LoadBalancer support

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

variable "metallb_namespace" {
  type        = string
  default     = "metallb-system"
  description = "MetalLB namespace"
}

variable "metallb_config" {
  type        = any
  description = "MetalLB configuration"
}

# Create namespace
resource "kubernetes_namespace" "metallb" {
  metadata {
    name = var.metallb_namespace
    labels = {
      "app.kubernetes.io/name" = "metallb"
      "app.kubernetes.io/part-of" = "metallb"
    }
  }
}

# Install MetalLB via Helm
resource "helm_release" "metallb" {
  name       = "metallb"
  repository = "https://metallb.github.io/metallb"
  chart      = "metallb"
  version    = "0.13.12"
  namespace  = kubernetes_namespace.metallb.metadata[0].name
  
  values = [
    yamlencode({
      namespace = {
        create = false  # Namespace already created
      }
    })
  ]
  
  depends_on = [
    kubernetes_namespace.metallb
  ]
}

# Create MetalLB ConfigMap
resource "kubernetes_config_map" "metallb_config" {
  metadata {
    name      = "config"
    namespace = kubernetes_namespace.metallb.metadata[0].name
  }

  data = {
    config = yamlencode({
      address-pools = var.metallb_config.address_pools
    })
  }

  depends_on = [
    helm_release.metallb
  ]
}

# Wait for MetalLB to be ready
resource "null_resource" "metallb_ready" {
  depends_on = [
    helm_release.metallb,
    kubernetes_config_map.metallb_config
  ]
  
  provisioner "local-exec" {
    command = "kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=metallb -n ${var.metallb_namespace} --timeout=300s"
  }
}
