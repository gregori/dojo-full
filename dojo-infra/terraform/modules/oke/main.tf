# Data source for availability domains and OKE images
data "oci_identity_availability_domains" "ads" {
  compartment_id = var.compartment_id
}

data "oci_containerengine_node_pool_option" "node_pool_options" {
  node_pool_option_id = "all"
}

# Dynamic OKE image selection (ARM64 / Always Free compatible)
locals {
  k8s_version_short  = replace(var.kubernetes_version, "v", "")
  oke_images         = jsondecode(jsonencode(data.oci_containerengine_node_pool_option.node_pool_options.sources))
  oke_image_id = try([
    for src in local.oke_images :
    src.image_id
    if try(regex(".*aarch.*OKE-${local.k8s_version_short}.*", src.source_name), null) != null
  ][0], data.oci_core_images.oke_images.images[0].id)
}

# Fallback image data source
data "oci_core_images" "oke_images" {
  compartment_id           = var.compartment_id
  operating_system         = "Oracle Linux"
  operating_system_version = "8"
  shape                    = var.node_shape
  sort_by                  = "TIMECREATED"
  sort_order               = "DESC"
}

# OKE Cluster
resource "oci_containerengine_cluster" "dojo_cluster" {
  compartment_id     = var.compartment_id
  name               = var.cluster_name
  vcn_id             = var.vcn_id
  kubernetes_version = var.kubernetes_version

  options {
    add_ons {
      is_kubernetes_dashboard_enabled = false
      is_tiller_enabled              = false
    }
    kubernetes_network_config {
      pods_cidr     = "10.244.0.0/16"
      services_cidr = "10.96.0.0/16"
    }
    service_lb_subnet_ids = [var.subnet_id]
  }

  endpoint_config {
    is_public_ip_enabled = true
    subnet_id            = var.subnet_id
  }
}

# Node Pool - spread across all ADs for Always Free capacity
resource "oci_containerengine_node_pool" "dojo_node_pool" {
  cluster_id         = oci_containerengine_cluster.dojo_cluster.id
  compartment_id     = var.compartment_id
  name               = var.node_pool_name
  kubernetes_version = var.kubernetes_version

  node_metadata = {
    user_data = base64encode(templatefile("${path.module}/files/node-pool-init.sh", {
      oke_init_script_url = "http://169.254.169.254/opc/v2/instance/metadata/oke_init_script"
    }))
  }

  node_config_details {
    dynamic "placement_configs" {
      for_each = data.oci_identity_availability_domains.ads.availability_domains
      content {
        availability_domain = placement_configs.value.name
        subnet_id          = var.node_subnet_id
      }
    }
    size = var.node_count
  }

  node_shape_config {
    ocpus         = var.node_ocpus
    memory_in_gbs = var.node_memory
  }

  node_shape = var.node_shape

  node_source_details {
    source_type             = "IMAGE"
    image_id                = local.oke_image_id
    boot_volume_size_in_gbs = var.boot_volume_size
  }

  initial_node_labels {
    key   = "name"
    value = var.cluster_name
  }

  ssh_public_key = var.ssh_public_key
}
