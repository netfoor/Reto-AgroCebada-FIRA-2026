terraform {
  required_version = ">= 1.11"

  # Estado remoto en el bucket que crea el repo infra-bootstrap.
  # El perfil sale de AWS_PROFILE al correr terraform init (el backend no lee var.perfil).
  backend "s3" {
    bucket       = "netfoor-tfstate-agrocebada-8cfmpm"
    key          = "agrocebada-uv/infra/terraform.tfstate"
    region       = "us-east-1"
    encrypt      = true
    use_lockfile = true
  }

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

provider "aws" {
  region  = var.region
  profile = var.perfil # null: credenciales del entorno (AWS_PROFILE, variables o SSO)

  default_tags {
    tags = {
      Proyecto    = "Reto AgroCebada 2026"
      Repositorio = "agrocebada-uv"
      Gestion     = "terraform"
    }
  }
}

# Los certificados que usa CloudFront deben estar en us-east-1, sea cual sea la región del resto.
provider "aws" {
  alias   = "us_east_1"
  region  = "us-east-1"
  profile = var.perfil

  default_tags {
    tags = {
      Proyecto    = "Reto AgroCebada 2026"
      Repositorio = "agrocebada-uv"
      Gestion     = "terraform"
    }
  }
}
