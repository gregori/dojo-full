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
    # Required because this node routes/masquerades pod-network traffic
    # (Flannel NAT) through this VNIC; OCI's source/dest check (default
    # on) rejects any packet whose source IP doesn't match the VNIC's
    # own address, which blocks all pod-initiated outbound connections.
    skip_source_dest_check = true
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

  lifecycle {
    ignore_changes = [
      metadata,
      # data.oci_core_images.k8s_image always resolves to the newest
      # published Oracle Linux 8 image, so this drifts on essentially
      # every plan. Confirmed the hard way: applying that "update" isn't
      # a metadata-only change -- it triggers a real boot volume
      # replacement (reimaging), which failed here on OCI's hypervisor
      # healthcheck precheck before completing. Boot source is a
      # launch-time-only concern for this node; never let a routine
      # plan/apply attempt to reimage it.
      source_details,
    ]
  }
}
