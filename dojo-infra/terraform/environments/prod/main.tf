terraform {
  required_providers {
    oci = {
      source  = "oracle/oci"
      version = ">= 5.0.0"
    }
  }
}

provider "oci" {
  tenancy_ocid     = var.tenancy_ocid
  user_ocid        = var.user_ocid
  fingerprint      = var.fingerprint
  private_key_path = var.private_key_path
  region           = var.region
}

# Data source for availability domain
locals {
  ad_name = var.availability_domain
}

# Networking Module
module "networking" {
  source = "../../modules/networking"

  compartment_id    = var.compartment_id
  vcn_cidr         = "10.0.0.0/16"
  availability_domain = local.ad_name
}

# Storage Module (for Terraform state and backups)
module "storage" {
  source = "../../modules/storage"

  compartment_id   = var.compartment_id
  bucket_name     = "dojo-terraform-state"
  bucket_namespace = var.bucket_namespace
}

# Container Registry Module
module "registry" {
  source = "../../modules/registry"

  compartment_id   = var.compartment_id
  region           = var.region
  repository_names = ["dojo-backend", "dojo-frontend"]
}

# Kubernetes Node (Compute Instance - manual kubeadm setup)
module "k8s_node" {
  source = "../../modules/k8s_node"

  compartment_id       = var.compartment_id
  subnet_id           = module.networking.public_subnet_id
  availability_domain  = local.ad_name
  node_shape          = "VM.Standard.A1.Flex"
  node_ocpus          = 4
  node_memory         = 24
  ssh_public_key_path = var.ssh_public_key_path
}
