output "vcn_id" {
  value = module.networking.vcn_id
}

output "public_subnet_id" {
  value = module.networking.public_subnet_id
}

output "cluster_id" {
  value = module.oke.cluster_id
}

output "cluster_endpoint" {
  value = module.oke.cluster_endpoint
}

output "node_pool_id" {
  value = module.oke.node_pool_id
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
