# Data source for OCI Services
data "oci_core_services" "all_oci_services" {
  filter {
    name   = "name"
    values = ["All .* Services In Oracle Services Network"]
    regex  = true
  }
}

# VCN
resource "oci_core_vcn" "dojo_vcn" {
  compartment_id = var.compartment_id
  cidr_block     = var.vcn_cidr
  display_name   = "dojo-vcn"
  dns_label      = "dojo"
}

# Internet Gateway
resource "oci_core_internet_gateway" "igw" {
  compartment_id = var.compartment_id
  vcn_id         = oci_core_vcn.dojo_vcn.id
  display_name   = "dojo-internet-gateway"
  enabled        = true
}

# NAT Gateway
resource "oci_core_nat_gateway" "nat" {
  compartment_id = var.compartment_id
  vcn_id         = oci_core_vcn.dojo_vcn.id
  display_name   = "dojo-nat-gateway"
}

# Service Gateway (for private subnet nodes to reach OCI services)
resource "oci_core_service_gateway" "sgw" {
  compartment_id = var.compartment_id
  vcn_id         = oci_core_vcn.dojo_vcn.id
  display_name   = "dojo-service-gateway"
  services {
    service_id = data.oci_core_services.all_oci_services.services[0].id
  }
}

# Public Subnet
resource "oci_core_subnet" "public_subnet" {
  compartment_id      = var.compartment_id
  vcn_id              = oci_core_vcn.dojo_vcn.id
  cidr_block          = "10.0.1.0/24"
  display_name        = "dojo-public-subnet"
  security_list_ids   = [oci_core_security_list.public_sl.id]
  route_table_id      = oci_core_route_table.public_rt.id
  dns_label           = "public"
}

# Private Subnet
resource "oci_core_subnet" "private_subnet" {
  compartment_id = var.compartment_id
  vcn_id         = oci_core_vcn.dojo_vcn.id
  cidr_block     = "10.0.2.0/24"
  display_name   = "dojo-private-subnet"
  security_list_ids   = [oci_core_security_list.private_sl.id]
  route_table_id      = oci_core_route_table.private_rt.id
  dns_label           = "private"
}

# Public Route Table
resource "oci_core_route_table" "public_rt" {
  compartment_id = var.compartment_id
  vcn_id         = oci_core_vcn.dojo_vcn.id
  display_name   = "dojo-public-route-table"

  route_rules {
    destination       = "0.0.0.0/0"
    destination_type  = "CIDR_BLOCK"
    network_entity_id = oci_core_internet_gateway.igw.id
  }
}

# Private Route Table
resource "oci_core_route_table" "private_rt" {
  compartment_id = var.compartment_id
  vcn_id         = oci_core_vcn.dojo_vcn.id
  display_name   = "dojo-private-route-table"

  route_rules {
    destination       = "0.0.0.0/0"
    destination_type  = "CIDR_BLOCK"
    network_entity_id = oci_core_nat_gateway.nat.id
  }
  route_rules {
    destination       = data.oci_core_services.all_oci_services.services[0].cidr_block
    destination_type  = "SERVICE_CIDR_BLOCK"
    network_entity_id = oci_core_service_gateway.sgw.id
  }
}

# Public Security List
resource "oci_core_security_list" "public_sl" {
  compartment_id = var.compartment_id
  vcn_id         = oci_core_vcn.dojo_vcn.id
  display_name   = "dojo-public-security-list"

  # Allow SSH
  ingress_security_rules {
    protocol  = "6" # TCP
    source    = "0.0.0.0/0"
    tcp_options {
      min = 22
      max = 22
    }
  }

  # Allow HTTP
  ingress_security_rules {
    protocol  = "6" # TCP
    source    = "0.0.0.0/0"
    tcp_options {
      min = 80
      max = 80
    }
  }

  # Allow HTTPS
  ingress_security_rules {
    protocol  = "6" # TCP
    source    = "0.0.0.0/0"
    tcp_options {
      min = 443
      max = 443
    }
  }

  # Allow Kubernetes API Server (from nodes through NAT)
  ingress_security_rules {
    protocol  = "6" # TCP
    source    = "0.0.0.0/0"
    tcp_options {
      min = 6443
      max = 6443
    }
  }

  # Allow all outbound
  egress_security_rules {
    protocol    = "all"
    destination = "0.0.0.0/0"
  }
}

# Cluster Endpoint Subnet (dedicated - prevents "service subnet" conflict)
resource "oci_core_subnet" "cluster_endpoint_subnet" {
  compartment_id      = var.compartment_id
  vcn_id              = oci_core_vcn.dojo_vcn.id
  cidr_block          = "10.0.5.0/24"
  display_name        = "dojo-cluster-endpoint-subnet"
  security_list_ids   = [oci_core_security_list.public_sl.id]
  route_table_id      = oci_core_route_table.public_rt.id
  dns_label           = "endpoint"
}

# Node Public Subnet (for OKE node pool - with IGW, not a service subnet)
resource "oci_core_subnet" "node_public_subnet" {
  compartment_id      = var.compartment_id
  vcn_id              = oci_core_vcn.dojo_vcn.id
  cidr_block          = "10.0.4.0/24"
  display_name        = "dojo-node-public-subnet"
  security_list_ids   = [oci_core_security_list.node_public_sl.id]
  route_table_id      = oci_core_route_table.node_public_rt.id
  dns_label           = "nodepublic"
}

# Node Public Route Table
resource "oci_core_route_table" "node_public_rt" {
  compartment_id = var.compartment_id
  vcn_id         = oci_core_vcn.dojo_vcn.id
  display_name   = "dojo-node-public-route-table"

  route_rules {
    destination       = "0.0.0.0/0"
    destination_type  = "CIDR_BLOCK"
    network_entity_id = oci_core_internet_gateway.igw.id
  }
}

# Node Public Security List
resource "oci_core_security_list" "node_public_sl" {
  compartment_id = var.compartment_id
  vcn_id         = oci_core_vcn.dojo_vcn.id
  display_name   = "dojo-node-public-security-list"

  # Allow all within VCN
  ingress_security_rules {
    protocol  = "all"
    source    = var.vcn_cidr
  }

  # Allow SSH from anywhere (troubleshooting)
  ingress_security_rules {
    protocol  = "6"
    source    = "0.0.0.0/0"
    tcp_options {
      min = 22
      max = 22
    }
  }

  # Allow all outbound (internet via IGW)
  egress_security_rules {
    protocol    = "all"
    destination = "0.0.0.0/0"
  }
}

# Private Security List
resource "oci_core_security_list" "private_sl" {
  compartment_id = var.compartment_id
  vcn_id         = oci_core_vcn.dojo_vcn.id
  display_name   = "dojo-private-security-list"

  # Allow all within VCN
  ingress_security_rules {
    protocol  = "all"
    source    = var.vcn_cidr
  }

  # Allow all outbound
  egress_security_rules {
    protocol    = "all"
    destination = "0.0.0.0/0"
  }
}
