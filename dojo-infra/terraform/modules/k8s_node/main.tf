data "oci_core_images" "k8s_image" {
  compartment_id           = var.compartment_id
  operating_system         = "Oracle Linux"
  operating_system_version = "8"
  shape                    = var.node_shape
  sort_by                  = "TIMECREATED"
  sort_order               = "DESC"
}

resource "oci_core_instance" "k8s_node" {
  compartment_id      = var.compartment_id
  availability_domain = var.availability_domain
  display_name        = "dojo-k8s-node"
  shape               = var.node_shape

  shape_config {
    ocpus         = var.node_ocpus
    memory_in_gbs = var.node_memory
  }

  create_vnic_details {
    subnet_id        = var.subnet_id
    assign_public_ip = true
    display_name     = "dojo-k8s-node-vnic"
  }

  source_details {
    source_type             = "image"
    source_id               = data.oci_core_images.k8s_image.images[0].id
    boot_volume_size_in_gbs = 100
  }

  metadata = {
    ssh_authorized_keys = file(var.ssh_public_key_path)
    user_data           = base64encode(file("${path.module}/user_data.sh"))
  }

  preserve_boot_volume = false
}
