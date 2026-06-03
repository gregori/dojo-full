# Local backend - state committed to git for CI/CD consistency.
# 
# To migrate to OCI Object Storage (S3-compatible):
# 1. Generate S3-compatible credentials in OCI Console:
#    (Identity → Users → User Details → Customer Secret Keys)
# 2. Add AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY to GitHub secrets
# 3. Uncomment the s3 backend below
# 4. Run: terraform init -migrate-state
#
# terraform {
#   backend "s3" {
#     bucket                      = "dojo-terraform-state"
#     key                         = "terraform.tfstate"
#     region                      = "sa-saopaulo-1"
#     endpoint                    = "https://grlidgqnerdm.compat.objectstorage.sa-saopaulo-1.oraclecloud.com"
#     skip_region_validation      = true
#     skip_credentials_validation = true
#     skip_metadata_api_check     = true
#     force_path_style            = true
#   }
# }

terraform {
  backend "local" {
    path = "terraform.tfstate"
  }
}
