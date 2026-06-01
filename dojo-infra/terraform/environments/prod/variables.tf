variable "tenancy_ocid" {
  description = "OCI Tenancy OCID"
  type        = string
}

variable "user_ocid" {
  description = "OCI User OCID"
  type        = string
}

variable "fingerprint" {
  description = "OCI API Key Fingerprint"
  type        = string
}

variable "private_key_path" {
  description = "Path to OCI API Private Key"
  type        = string
  default     = "~/.oci/oci_api_key.pem"
}

variable "region" {
  description = "OCI Region"
  type        = string
  default     = "sa-saopaulo-1"
}

variable "compartment_id" {
  description = "OCI Compartment ID"
  type        = string
}

variable "availability_domain" {
  description = "Availability Domain"
  type        = string
}

variable "bucket_namespace" {
  description = "Object Storage Namespace"
  type        = string
}


