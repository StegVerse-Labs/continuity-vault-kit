terraform {
  required_version = ">= 1.6.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      System      = "reconstructive-ai-memory"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

resource "aws_kms_key" "stegid_verification" {
  description              = "StegID asymmetric signing and verification key"
  key_usage                = "SIGN_VERIFY"
  customer_master_key_spec = "ECC_NIST_P256"
  enable_key_rotation      = false
  deletion_window_in_days  = var.kms_deletion_window_days
}

resource "aws_kms_alias" "stegid_verification" {
  name          = "alias/${var.name_prefix}-stegid-verification"
  target_key_id = aws_kms_key.stegid_verification.key_id
}

resource "aws_kms_key" "memory_custody" {
  description              = "Reconstructive memory wrapping and custody key"
  key_usage                = "ENCRYPT_DECRYPT"
  customer_master_key_spec = "SYMMETRIC_DEFAULT"
  enable_key_rotation      = true
  deletion_window_in_days  = var.kms_deletion_window_days
}

resource "aws_kms_alias" "memory_custody" {
  name          = "alias/${var.name_prefix}-memory-custody"
  target_key_id = aws_kms_key.memory_custody.key_id
}

resource "aws_dynamodb_table" "authoritative_state" {
  name         = "${var.name_prefix}-authoritative-state"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "state_key"

  attribute {
    name = "state_key"
    type = "S"
  }

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled     = true
    kms_key_arn = aws_kms_key.memory_custody.arn
  }

  deletion_protection_enabled = var.deletion_protection_enabled
}

variable "aws_region" {
  description = "AWS region for KMS and DynamoDB resources."
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Deployment environment."
  type        = string
  default     = "staging"
  validation {
    condition     = contains(["staging", "production"], var.environment)
    error_message = "environment must be staging or production"
  }
}

variable "name_prefix" {
  description = "Resource naming prefix."
  type        = string
  default     = "stegverse-reconstructive-memory"
}

variable "kms_deletion_window_days" {
  description = "Governed delay before a scheduled KMS deletion completes."
  type        = number
  default     = 30
  validation {
    condition     = var.kms_deletion_window_days >= 7 && var.kms_deletion_window_days <= 30
    error_message = "KMS deletion window must be between 7 and 30 days"
  }
}

variable "deletion_protection_enabled" {
  description = "Protect the authoritative table from accidental deletion."
  type        = bool
  default     = true
}

output "stegid_kms_key_arn" {
  value       = aws_kms_key.stegid_verification.arn
  description = "Populate providers.stegid_verification.resource_id with this ARN."
}

output "custody_kms_key_arn" {
  value       = aws_kms_key.memory_custody.arn
  description = "Populate providers.key_custody.resource_id with this ARN."
}

output "authoritative_state_table_arn" {
  value       = aws_dynamodb_table.authoritative_state.arn
  description = "Populate providers.replicated_state.resource_id with this ARN."
}

output "activation_profile_fragment" {
  description = "Non-secret resource mapping for the production activation profile."
  value = {
    aws_region                    = var.aws_region
    stegid_verification_resource = aws_kms_key.stegid_verification.arn
    key_custody_resource         = aws_kms_key.memory_custody.arn
    replicated_state_resource    = aws_dynamodb_table.authoritative_state.arn
  }
}
