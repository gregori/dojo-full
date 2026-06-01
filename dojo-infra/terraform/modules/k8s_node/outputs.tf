output "instance_id" {
  value = oci_core_instance.k8s_node.id
}

output "public_ip" {
  value = oci_core_instance.k8s_node.public_ip
}

output "private_ip" {
  value = oci_core_instance.k8s_node.private_ip
}
