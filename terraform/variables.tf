variable "aws_region" {
  type        = string
  description = "The AWS region to deploy resources to."
  default     = "eu-west-2" # London region (matches LSEG theme)
}

variable "environment" {
  type        = string
  description = "Deployment environment name."
  default     = "dev"
}
