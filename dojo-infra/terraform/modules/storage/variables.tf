variable "compartment_id" {
  description = "OCI Compartment ID"
  type        = string
}

variable "bucket_name" {
  description = "Object Storage Bucket Name"
  type        = string
  default     = "dojo-terraform-state"
}

variable "bucket_namespace" {
  description = "Object Storage Namespace"
  type        = string
}

output "bucket_id" {
  value = oci_objectstorage_bucket.terraform_state.id
}

output "bucket_name" {
  value = oci_objectstorage_bucket.terraform_state.name
}

output "bucket_namespace" {
  value = var.bucket_namespace
}
