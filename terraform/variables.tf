# Input variables for K3s on-premises platform

variable "cluster_name" {
  type        = string
  default     = "k3s-platform"
  description = "Name of the Kubernetes cluster"
}

variable "kubeconfig_path" {
  type        = string
  default     = "~/.kube/config-k3s"
  description = "Path to kubeconfig used by Terraform Kubernetes/Helm providers"
}

variable "kubernetes_version" {
  type        = string
  default     = "1.29.0"
  description = "Kubernetes version to deploy"
}

variable "vm_memory" {
  type        = string
  default     = "2G"
  description = "Memory allocated to each VM"
}

variable "vm_cpu" {
  type        = string
  default     = "2"
  description = "CPU cores allocated to each VM"
}

variable "vm_disk" {
  type        = string
  default     = "20G"
  description = "Disk size allocated to each VM"
}

variable "network_cidr" {
  type        = string
  default     = "192.168.56.0/24"
  description = "Network CIDR for the cluster"
}

variable "metallb_pool" {
  type        = string
  default     = "192.168.56.240-192.168.56.250"
  description = "IP range for MetalLB LoadBalancer services"
}

variable "control_plane_nodes" {
  type = map(object({
    ip   = string
    role = string
  }))
  default = {
    cp1 = {
      ip   = "192.168.56.101"
      role = "controlplane"
    }
    cp2 = {
      ip   = "192.168.56.102"
      role = "controlplane"
    }
  }
  description = "Control plane node configuration"
}

variable "worker_nodes" {
  type = map(object({
    ip   = string
    role = string
  }))
  default = {
    worker1 = {
      ip   = "192.168.56.104"
      role = "worker"
    }
    worker2 = {
      ip   = "192.168.56.105"
      role = "worker"
    }
  }
  description = "Worker node configuration"
}

variable "argocd_namespace" {
  type        = string
  default     = "argocd"
  description = "Namespace for ArgoCD"
}

variable "argocd_version" {
  type        = string
  default     = "v5.53.0"
  description = "ArgoCD Helm chart version"
}

variable "metallb_namespace" {
  type        = string
  default     = "metallb-system"
  description = "Namespace for MetalLB"
}

variable "metallb_version" {
  type        = string
  default     = "0.13.12"
  description = "MetalLB Helm chart version"
}
