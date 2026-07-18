terraform {
  required_version = "~> 1.15.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.55"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  # 値はここに書かず `terraform init -backend-config=backend.hcl` で注入する
  # (backend.hcl.example を参照。backend.hcl 自体は .gitignore 済み)
  backend "s3" {}
}
