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

# OKE Cluster (Managed Kubernetes)
module "oke" {
  source = "../../modules/oke"

  compartment_id      = var.compartment_id
  vcn_id              = module.networking.vcn_id
  subnet_id           = module.networking.cluster_endpoint_subnet_id
  node_subnet_id      = module.networking.node_public_subnet_id
  availability_domain = local.ad_name
  cluster_name        = "dojo-cluster"
  node_pool_name      = "dojo-node-pool"
  node_shape          = "VM.Standard.A1.Flex"
  node_ocpus          = 4
  node_memory         = 24
  node_count          = 1
}
