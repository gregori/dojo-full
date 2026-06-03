# OCI Object Storage (S3-compatible) backend
# Credentials set as AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY GitHub secrets
# (OCI Customer Secret Keys, mapped to AWS env vars for Terraform S3 backend compat)
terraform {
  backend "s3" {
    bucket                      = "dojo-terraform-state"
    key                         = "terraform.tfstate"
    region                      = "sa-saopaulo-1"
    endpoint                    = "https://grlidgqnerdm.compat.objectstorage.sa-saopaulo-1.oraclecloud.com"
    skip_region_validation      = true
    skip_credentials_validation = true
    skip_metadata_api_check     = true
    force_path_style            = true
  }
}
