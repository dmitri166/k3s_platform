# ArgoCD Applications module for GitOps application deployment

terraform {
  required_providers {
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.23"
    }
  }
}

variable "kubeconfig" {
  type        = string
  description = "Kubernetes kubeconfig content"
}

variable "applications" {
  type        = map(any)
  description = "Map of ArgoCD applications to deploy"
}

provider "kubernetes" {
  config_path = var.kubeconfig
}

# Create ArgoCD Application for each application
resource "kubernetes_manifest" "argocd_applications" {
  for_each = var.applications
  
  manifest = {
    apiVersion = "argoproj.io/v1alpha1"
    kind       = "Application"
    
    metadata = {
      name      = each.key
      namespace = "argocd"
      labels = {
        "app.kubernetes.io/name" = each.key
        "app.kubernetes.io/part-of" = "argocd"
      }
    }
    
    spec = {
      project = "default"
      
      source = {
        repoURL = "https://github.com/yourusername/talos_platform.git"
        targetRevision = "HEAD"
        path = each.value.path
      }
      
      destination = {
        server = "https://kubernetes.default.svc"
        namespace = each.value.namespace
      }
      
      syncPolicy = {
        automated = {
          prune = true
          selfHeal = true
        }
        syncOptions = [
          "CreateNamespace=true"
        ]
      }
    }
  }
}

# Wait for applications to be synced
resource "null_resource" "applications_ready" {
  depends_on = [
    kubernetes_manifest.argocd_applications
  ]
  
  provisioner "local-exec" {
    command = "kubectl wait --for=condition=Healthy application --all -n argocd --timeout=600s"
  }
}
