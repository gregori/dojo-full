variable "compartment_id" {
  description = "OCI Compartment ID"
  type        = string
}

variable "vcn_cidr" {
  description = "CIDR block for VCN"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_domain" {
  description = "Availability Domain for resources"
  type        = string
}

output "vcn_id" {
  value = oci_core_vcn.dojo_vcn.id
}

output "public_subnet_id" {
  value = oci_core_subnet.public_subnet.id
}

output "private_subnet_id" {
  value = oci_core_subnet.private_subnet.id
}

output "internet_gateway_id" {
  value = oci_core_internet_gateway.igw.id
}

output "nat_gateway_id" {
  value = oci_core_nat_gateway.nat.id
}

output "service_gateway_id" {
  value = oci_core_service_gateway.sgw.id
}

output "cluster_endpoint_subnet_id" {
  value = oci_core_subnet.cluster_endpoint_subnet.id
}

output "node_public_subnet_id" {
  value = oci_core_subnet.node_public_subnet.id
}
