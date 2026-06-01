resource "oci_artifacts_container_repository" "dojo_repos" {
  for_each = toset(var.repository_names)

  compartment_id = var.compartment_id
  display_name   = each.value
  is_public      = false
}
