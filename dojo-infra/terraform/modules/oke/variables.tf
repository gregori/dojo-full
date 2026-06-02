variable "compartment_id" {
  description = "OCI Compartment ID"
  type        = string
}

variable "vcn_id" {
  description = "VCN ID"
  type        = string
}

variable "subnet_id" {
  description = "Subnet ID for cluster endpoint and service LB"
  type        = string
}

variable "node_subnet_id" {
  description = "Subnet ID for node pool placement"
  type        = string
}

variable "availability_domain" {
  description = "Availability Domain"
  type        = string
}

variable "cluster_name" {
  description = "OKE Cluster Name"
  type        = string
  default     = "dojo-cluster"
}

variable "kubernetes_version" {
  description = "Kubernetes version"
  type        = string
  default     = "v1.34.2"
}

variable "node_pool_name" {
  description = "Node Pool Name"
  type        = string
  default     = "dojo-node-pool"
}

variable "node_count" {
  description = "Number of nodes"
  type        = number
  default     = 2
}

variable "node_shape" {
  description = "Shape for nodes"
  type        = string
  default     = "VM.Standard.A1.Flex" # ARM Always Free
}

variable "node_ocpus" {
  description = "OCPUs per node"
  type        = number
  default     = 2
}

variable "node_memory" {
  description = "Memory per node (GB)"
  type        = number
  default     = 12
}

variable "boot_volume_size" {
  description = "Boot volume size per node (GB)"
  type        = number
  default     = 100
}

variable "ssh_public_key" {
  description = "SSH public key for node access"
  type        = string
  default     = ""
}

output "cluster_id" {
  value = oci_containerengine_cluster.dojo_cluster.id
}

output "cluster_endpoint" {
  value = oci_containerengine_cluster.dojo_cluster.endpoints[0].public_endpoint
}

output "node_pool_id" {
  value = oci_containerengine_node_pool.dojo_node_pool.id
}
