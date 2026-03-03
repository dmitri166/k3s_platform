# Main Terraform configuration for K3s on-premises platform
# Simplified configuration for hybrid deployment approach

terraform {
  required_version = ">= 1.5.0"

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

# Local values and configuration
locals {
  cluster_name = var.cluster_name
  namespace    = "k3s-platform"

  # Network configuration
  network_cidr = var.network_cidr
  metallb_pool = var.metallb_pool

  # K3s version
  kubernetes_version = var.kubernetes_version

  # Paths
  kubeconfig_path = var.kubeconfig_path

  # All nodes
  all_nodes = merge(var.control_plane_nodes, var.worker_nodes)
}

# MetalLB module
module "metallb" {
  source = "./modules/metallb"

  metallb_namespace = "metallb-system"
  address_pool_name = "default"
  address_pool_cidr = local.metallb_pool
}

# ArgoCD module
module "argocd" {
  source = "./modules/argocd"

  depends_on = [
    module.metallb
  ]

  argocd_namespace = "argocd"

  argocd_helm_config = {
    repository = "https://argoproj.github.io/argo-helm"
    chart      = "argo-cd"
    version    = "v5.53.0"
  }

  argocd_values = yamldecode(file("${path.root}/../argocd/values.yaml"))
}
