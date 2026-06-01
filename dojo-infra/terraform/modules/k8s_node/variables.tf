variable "compartment_id" {
  description = "OCI Compartment ID"
  type        = string
}

variable "subnet_id" {
  description = "Subnet ID for the compute instance"
  type        = string
}

variable "availability_domain" {
  description = "Availability Domain"
  type        = string
}

variable "node_shape" {
  description = "Compute shape"
  type        = string
  default     = "VM.Standard.A1.Flex"
}

variable "node_ocpus" {
  description = "OCPUs"
  type        = number
  default     = 4
}

variable "node_memory" {
  description = "Memory in GB"
  type        = number
  default     = 24
}

variable "ssh_public_key_path" {
  description = "Path to SSH public key"
  type        = string
}
