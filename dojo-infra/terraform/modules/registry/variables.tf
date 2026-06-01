variable "compartment_id" {
  description = "OCI Compartment ID"
  type        = string
}

variable "region" {
  description = "OCI Region for OCIR URL"
  type        = string
}

variable "repository_names" {
  description = "List of repository names to create"
  type        = list(string)
  default     = ["dojo-backend", "dojo-frontend"]
}

output "repository_urls" {
  value = {
    for repo in oci_artifacts_container_repository.dojo_repos :
    repo.display_name => "${var.region}.ocir.io/${repo.namespace}/${repo.display_name}"
  }
}
