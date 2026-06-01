# Initial local backend - migrate to S3 after bucket creation
terraform {
  backend "local" {
    path = "terraform.tfstate"
  }
}
