# Provider configurations for Talos on-premises platform

# Multipass provider for VM management
provider "multipass" {
  # Default provider configuration
}

# Talos provider for cluster management
provider "talos" {
  # Configuration will be set after cluster bootstrap
}

# Helm provider for Kubernetes package management
provider "helm" {
  # Configuration will be set after cluster bootstrap
}
