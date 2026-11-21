terraform {
  required_version = ">= 1.0.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# Generate a random suffix for the S3 bucket to ensure global uniqueness
resource "random_id" "bucket_suffix" {
  byte_length = 4
}

# AWS S3 Bucket for storing application logs / backups
resource "aws_s3_bucket" "log_bucket" {
  bucket        = "lseg-sre-portfolio-logs-${random_id.bucket_suffix.hex}"
  force_destroy = true

  tags = {
    Name        = "SRE Portfolio Log Bucket"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# Enable versioning for log files (SRE resilience practice)
resource "aws_s3_bucket_versioning" "log_bucket_versioning" {
  bucket = aws_s3_bucket.log_bucket.id
  versioning_configuration {
    status = "Enabled"
  }
}

# Block all public access (SRE security best practice)
resource "aws_s3_bucket_public_access_block" "log_bucket_public_block" {
  bucket = aws_s3_bucket.log_bucket.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Enable default server-side encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "log_bucket_encryption" {
  bucket = aws_s3_bucket.log_bucket.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}
