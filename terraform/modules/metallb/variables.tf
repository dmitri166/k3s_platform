# Variables for MetalLB module

variable "metallb_namespace" {
  type        = string
  default     = "metallb-system"
  description = "MetalLB namespace"
}

variable "metallb_config" {
  type        = any
  description = "MetalLB configuration"
}
