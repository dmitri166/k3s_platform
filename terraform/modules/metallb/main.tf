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

# Create namespace
resource "kubernetes_namespace" "metallb" {
  metadata {
    name = var.metallb_namespace
    labels = {
      "app.kubernetes.io/name"    = "metallb"
      "app.kubernetes.io/part-of" = "k3s-platform"
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
        create = false # Namespace already created
      }
    })
  ]

  depends_on = [
    kubernetes_namespace.metallb
  ]
}

resource "kubernetes_manifest" "metallb_ipaddress_pool" {
  manifest = {
    apiVersion = "metallb.io/v1beta1"
    kind       = "IPAddressPool"
    metadata = {
      name      = var.address_pool_name
      namespace = kubernetes_namespace.metallb.metadata[0].name
    }
    spec = {
      addresses = [var.address_pool_cidr]
    }
  }

  depends_on = [
    helm_release.metallb
  ]
}

resource "kubernetes_manifest" "metallb_l2_advertisement" {
  manifest = {
    apiVersion = "metallb.io/v1beta1"
    kind       = "L2Advertisement"
    metadata = {
      name      = "${var.address_pool_name}-l2"
      namespace = kubernetes_namespace.metallb.metadata[0].name
    }
    spec = {
      ipAddressPools = [var.address_pool_name]
    }
  }

  depends_on = [
    kubernetes_manifest.metallb_ipaddress_pool
  ]
}

