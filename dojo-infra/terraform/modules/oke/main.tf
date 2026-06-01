# Data source for latest OKE image
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
    service_lb_config {
      freeform_tags = {}
    }
    service_lb_subnet_ids = [var.subnet_id]
  }

  endpoint_config {
    is_public_ip_enabled = true
    subnet_id            = var.subnet_id
  }
}

# Node Pool
resource "oci_containerengine_node_pool" "dojo_node_pool" {
  cluster_id         = oci_containerengine_cluster.dojo_cluster.id
  compartment_id     = var.compartment_id
  name               = var.node_pool_name
  kubernetes_version = var.kubernetes_version

  node_config_details {
    placement_configs {
      availability_domain = var.availability_domain
      subnet_id          = var.node_subnet_id
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
    image_id                = data.oci_core_images.oke_images.images[0].id
    boot_volume_size_in_gbs = 120
  }
}
