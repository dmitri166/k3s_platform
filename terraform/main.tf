# Main Terraform configuration for Talos on-premises platform

terraform {
  required_version = ">= 1.5.0"
  
  required_providers {
    multipass = {
      source  = "larstabe/multipass"
      version = "~> 1.2"
    }
    talos = {
      source  = "siderolabs/talos"
      version = "~> 0.5"
    }
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
    local = {
      source  = "hashicorp/local"
      version = "~> 2.4"
    }
    null = {
      source  = "hashicorp/null"
      version = "~> 3.2"
    }
  }
}

# Local values and configuration
locals {
  cluster_name = var.cluster_name
  namespace    = "talos-platform"
  
  # Network configuration
  network_cidr = var.network_cidr
  metallb_pool = var.metallb_pool
  
  # VM configuration
  vm_memory = var.vm_memory
  vm_cpu    = var.vm_cpu
  vm_disk   = var.vm_disk
  
  # Talos version
  talos_version = var.talos_version
  kubernetes_version = var.kubernetes_version
  
  # Paths
  kubeconfig_path = "${path.root}/kubeconfig"
  talosconfig_path = "${path.root}/talosconfig"
  
  # All nodes
  all_nodes = merge(var.control_plane_nodes, var.worker_nodes)
}

# Generate cluster secrets
resource "talos_machine_secret" "this" {
  version = local.talos_version
}

# Create Multipass VMs
resource "multipass_instance" "vms" {
  for_each = local.all_nodes
  
  name  = each.key
  cpus  = local.vm_cpu
  memory = local.vm_memory
  disk  = local.vm_disk
  
  # Add network configuration
  networks {
    name = "bridged"
  }
  
  # Wait for VM to be ready
  provisioner "local-exec" {
    command = "multipass exec ${each.key} -- sudo apt-get update && sudo apt-get install -y curl"
  }
}

# Generate Talos machine configurations for control plane
resource "talos_machine_configuration" "controlplane" {
  for_each = var.control_plane_nodes
  
  cluster_name     = local.cluster_name
  cluster_endpoint = "https://${var.control_plane_nodes["cp1"].ip}:6443"
  machine_type     = "controlplane"
  machine_secrets  = talos_machine_secret.this.machine_secrets
  
  config_patches = [
    yamlencode({
      version = local.talos_version
      persist = true
      machine = {
        type = "controlplane"
        network = {
          hostname = each.key
          interfaces = [
            {
              device = "eth0"
              cidr = "${each.value.ip}/24"
            }
          ]
        }
        install = {
          disk = "/dev/sda"
          image = "ghcr.io/siderolabs/talos:${local.talos_version}"
        }
        kubelet = {
          extraArgs = {
            "node-ip" = each.value.ip
          }
        }
      }
      cluster = {
        controlPlane = {
          endpoint = "https://${local.control_plane_nodes["cp1"].ip}:6443"
          localAPIServerPort = 6443
        }
        network = {
          pod = {
            cidrs = ["10.244.0.0/16"]
          }
          service = {
            cidrs = ["10.96.0.0/12"]
          }
        }
        apiServer = {
          certSANs = [
            local.control_plane_nodes["cp1"].ip,
            local.control_plane_nodes["cp2"].ip,
            local.control_plane_nodes["cp3"].ip,
            "127.0.0.1",
            "kubernetes",
            "kubernetes.default",
            "kubernetes.default.svc",
            "kubernetes.default.svc.cluster.local"
          ]
        }
      }
    })
  ]
}

# Generate Talos machine configurations for workers
resource "talos_machine_configuration" "worker" {
  for_each = var.worker_nodes
  
  cluster_name     = local.cluster_name
  cluster_endpoint = "https://${var.control_plane_nodes["cp1"].ip}:6443"
  machine_type     = "worker"
  machine_secrets  = talos_machine_secret.this.machine_secrets
  
  config_patches = [
    yamlencode({
      version = local.talos_version
      persist = true
      machine = {
        type = "worker"
        network = {
          hostname = each.key
          interfaces = [
            {
              device = "eth0"
              cidr = "${each.value.ip}/24"
            }
          ]
        }
        install = {
          disk = "/dev/sda"
          image = "ghcr.io/siderolabs/talos:${local.talos_version}"
        }
        kubelet = {
          extraArgs = {
            "node-ip" = each.value.ip
          }
        }
      }
      cluster = {
        network = {
          pod = {
            cidrs = ["10.244.0.0/16"]
          }
          service = {
            cidrs = ["10.96.0.0/12"]
          }
        }
      }
    })
  ]
}

# Apply Talos configurations to VMs
resource "null_resource" "apply_talos_config" {
  for_each = local.all_nodes
  
  depends_on = [
    multipass_instance.vms,
    talos_machine_configuration.controlplane,
    talos_machine_configuration.worker
  ]
  
  provisioner "local-exec" {
    command = "talosctl apply-config -n ${each.value.ip} -f ${each.key == "cp1" ? talos_machine_configuration.controlplane[each.key].machine_config : talos_machine_configuration.worker[each.key].machine_config}"
  }
}

# Bootstrap the cluster
resource "null_resource" "bootstrap_cluster" {
  depends_on = [
    null_resource.apply_talos_config
  ]
  
  provisioner "local-exec" {
    command = "talosctl bootstrap -n ${var.control_plane_nodes["cp1"].ip}"
  }
  
  # Wait for cluster to be ready
  provisioner "local-exec" {
    command = "sleep 60"
  }
}

# Generate kubeconfig
resource "null_resource" "generate_kubeconfig" {
  depends_on = [
    null_resource.bootstrap_cluster
  ]
  
  provisioner "local-exec" {
    command = "talosctl kubeconfig -n ${var.control_plane_nodes["cp1"].ip} > ${local.kubeconfig_path}"
  }
}

# Generate ArgoCD admin password
resource "random_password" "argocd_admin" {
  length  = 16
  special = true
}

# Create namespaces using kubectl
resource "null_resource" "create_namespaces" {
  depends_on = [
    null_resource.generate_kubeconfig
  ]
  
  provisioner "local-exec" {
    command = "kubectl create namespace platform --dry-run=client -o yaml | kubectl apply -f -"
  }
  
  provisioner "local-exec" {
    command = "kubectl create namespace monitoring --dry-run=client -o yaml | kubectl apply -f -"
  }
  
  provisioner "local-exec" {
    command = "kubectl create namespace security --dry-run=client -o yaml | kubectl apply -f -"
  }
  
  provisioner "local-exec" {
    command = "kubectl create namespace velero --dry-run=client -o yaml | kubectl apply -f -"
  }
  
  provisioner "local-exec" {
    command = "kubectl create namespace vault --dry-run=client -o yaml | kubectl apply -f -"
  }
}

# MetalLB module
module "metallb" {
  source = "./modules/metallb"
  
  depends_on = [
    null_resource.create_namespaces
  ]
  
  metallb_namespace = "metallb-system"
  
  metallb_config = {
    address_pools = [
      {
        name = "default"
        protocol = "layer2"
        addresses = [local.metallb_pool]
      }
    ]
  }
}

# ArgoCD module
module "argocd" {
  source = "./modules/argocd"
  
  depends_on = [
    module.metallb,
    null_resource.create_namespaces
  ]
  
  argocd_namespace = "argocd"
  
  argocd_helm_config = {
    repository = "https://argoproj.github.io/argo-helm"
    chart      = "argo-cd"
    version    = "v5.53.0"
  }
  
  argocd_values = {
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
      config = {
        repositories = {
          talos_platform = {
            url = "https://github.com/yourusername/talos_platform.git"
          }
        }
        "application.resourceTrackingMethod" = "annotation"
        "timeout.reconciliation" = "180s"
      }
    }
    
    configs = {
      cm = {
        "application.resourceTrackingMethod" = "annotation"
        "timeout.reconciliation" = "180s"
      }
    }
    
    notifications = {
      enabled = true
    }
    
    dex = {
      enabled = false
    }
  }
}

# ArgoCD applications module
module "argocd_applications" {
  source = "./modules/argocd-applications"
  
  depends_on = [
    module.argocd,
    null_resource.create_namespaces
  ]
  
  kubeconfig = local.kubeconfig_path
  
  applications = {
    # Core infrastructure
    namespaces = {
      path = "namespaces"
      namespace = "argocd"
    }
    
    # Networking
    ingress_nginx = {
      path = "apps/ingress-nginx"
      namespace = "ingress-nginx"
    }
    
    cert_manager = {
      path = "apps/cert-manager"
      namespace = "cert-manager"
    }
    
    # Monitoring
    monitoring = {
      path = "apps/kube-prometheus-stack"
      namespace = "monitoring"
    }
    
    loki = {
      path = "apps/loki-stack"
      namespace = "monitoring"
    }
    
    # Security
    opa_gatekeeper = {
      path = "apps/opa-gatekeeper"
      namespace = "gatekeeper-system"
    }
    
    falco = {
      path = "apps/falco"
      namespace = "falco"
    }
    
    # Backup
    velero = {
      path = "apps/velero"
      namespace = "velero"
    }
    
    # Secrets management
    vault = {
      path = "apps/vault"
      namespace = "vault"
    }
    
    external_secrets = {
      path = "apps/external-secrets"
      namespace = "external-secrets"
    }
  }
}
