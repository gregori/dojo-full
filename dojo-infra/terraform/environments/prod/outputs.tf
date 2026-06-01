output "vcn_id" {
  value = module.networking.vcn_id
}

output "public_subnet_id" {
  value = module.networking.public_subnet_id
}

output "k8s_node_instance_id" {
  value = module.k8s_node.instance_id
}

output "k8s_node_public_ip" {
  value = module.k8s_node.public_ip
}

output "k8s_node_private_ip" {
  value = module.k8s_node.private_ip
}

output "repository_urls" {
  value = module.registry.repository_urls
}

output "bucket_name" {
  value = module.storage.bucket_name
}

output "bucket_namespace" {
  value = module.storage.bucket_namespace
}
