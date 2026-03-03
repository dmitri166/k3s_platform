# Variables for MetalLB module

variable "metallb_namespace" {
  type        = string
  default     = "metallb-system"
  description = "MetalLB namespace"
}

variable "address_pool_name" {
  type        = string
  default     = "default"
  description = "MetalLB IPAddressPool name"
}

variable "address_pool_cidr" {
  type        = string
  description = "MetalLB address range, e.g. 192.168.56.240-192.168.56.250"
}
