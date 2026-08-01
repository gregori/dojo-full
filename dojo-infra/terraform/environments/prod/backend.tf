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
    skip_requesting_account_id  = true
    force_path_style            = true
    # OCI's S3-compatible endpoint returns 501 NotImplemented for the
    # aws-chunked/checksum-trailer PutObject encoding aws-sdk-go-v2 sends
    # by default (https://github.com/hashicorp/terraform/issues/34053).
    # This backend-native flag (added in Terraform 1.6.4) disables it;
    # the AWS_REQUEST_CHECKSUM_CALCULATION/AWS_RESPONSE_CHECKSUM_VALIDATION
    # env vars previously tried do not cover this code path and had no effect.
    skip_s3_checksum = true
  }
}
