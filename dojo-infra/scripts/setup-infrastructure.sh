#!/bin/bash
set -e

echo "=== Dojo Admin - OCI Infrastructure Setup ==="
echo ""

# Check prerequisites
command -v terraform >/dev/null 2>&1 || { echo "Terraform is required but not installed. Aborting." >&2; exit 1; }
command -v oci >/dev/null 2>&1 || { echo "OCI CLI is required but not installed. Aborting." >&2; exit 1; }

# Get OCI configuration
read -p "Enter your OCI Tenancy OCID: " TENANCY_OCID
read -p "Enter your OCI User OCID: " USER_OCID
read -p "Enter your OCI API Key Fingerprint: " FINGERPRINT
read -p "Enter your OCI Compartment ID: " COMPARTMENT_ID
read -p "Enter your OCI Availability Domain (e.g., Uocm:SA-SAOPAULO-1-AD-1): " AVAILABILITY_DOMAIN
read -p "Enter your Object Storage Namespace: " BUCKET_NAMESPACE
read -p "Enter path to your OCI API Private Key [~/.oci/oci_api_key.pem]: " PRIVATE_KEY_PATH
PRIVATE_KEY_PATH=${PRIVATE_KEY_PATH:-~/.oci/oci_api_key.pem}

echo ""
echo "=== Initializing Terraform ==="
cd terraform/environments/prod

# Create terraform.tfvars
cat > terraform.tfvars <<EOF
tenancy_ocid     = "$TENANCY_OCID"
user_ocid        = "$USER_OCID"
fingerprint      = "$FINGERPRINT"
private_key_path = "$PRIVATE_KEY_PATH"
compartment_id   = "$COMPARTMENT_ID"
availability_domain = "$AVAILABILITY_DOMAIN"
region           = "sa-saopaulo-1"
bucket_namespace = "$BUCKET_NAMESPACE"
EOF

echo "=== Terraform Init ==="
terraform init

echo "=== Terraform Plan ==="
terraform plan

echo ""
read -p "Do you want to apply these changes? (yes/no): " CONFIRM
if [[ $CONFIRM == "yes" ]]; then
    echo "=== Applying Infrastructure ==="
    terraform apply -auto-approve
    
    echo ""
    echo "=== Infrastructure Created ==="
    echo "Cluster ID: $(terraform output -raw cluster_id)"
    echo "Cluster Endpoint: $(terraform output -raw cluster_endpoint)"
    echo "Bucket Name: $(terraform output -raw bucket_name)"
    echo ""
    echo "Next steps:"
    echo "1. Configure kubectl: oci ce cluster create-kubeconfig --cluster-id $(terraform output -raw cluster_id) --file ~/.kube/config"
    echo "2. Update k8s manifests with your image registry URLs"
    echo "3. Apply manifests: kubectl apply -k k8s/"
else
    echo "Apply cancelled."
fi
