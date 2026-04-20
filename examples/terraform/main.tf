terraform {
  required_version = ">= 1.0"

  backend "local" {
    path = "terraform.tfstate"
  }

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

resource "aws_s3_bucket" "assets" {
  bucket = "my-app-assets-${var.environment}"

  tags = {
    Environment = var.environment
  }
}

resource "aws_instance" "app" {
  count         = 2
  ami           = var.ami_id
  instance_type = var.instance_type

  tags = {
    Name        = "app-server-${count.index + 1}"
    Environment = var.environment
  }
}
