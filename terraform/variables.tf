# ==============================================================================
# ContextOS — Terraform Variables
# ==============================================================================
# These variables parameterize the infrastructure. Override defaults by:
#   1. CLI flags:     terraform apply -var="aws_region=us-west-2"
#   2. tfvars file:   terraform apply -var-file="staging.tfvars"
#   3. Environment:   export TF_VAR_aws_region=us-west-2
# ==============================================================================

variable "aws_region" {
  description = "AWS region where all resources will be created"
  type        = string
  default     = "us-east-1"

  validation {
    condition     = can(regex("^(us|eu|ap|sa|ca|me|af)-(north|south|east|west|central|northeast|southeast)-[0-9]+$", var.aws_region))
    error_message = "Must be a valid AWS region (e.g., us-east-1, eu-west-2)."
  }
}

variable "cluster_name" {
  description = "Name of the EKS cluster (used in resource names and tags)"
  type        = string
  default     = "contextos-cluster"

  validation {
    condition     = can(regex("^[a-z0-9-]+$", var.cluster_name))
    error_message = "Cluster name must contain only lowercase letters, numbers, and hyphens."
  }
}

variable "environment" {
  description = "Deployment environment (used in tags for cost tracking and access control)"
  type        = string
  default     = "production"

  validation {
    condition     = contains(["development", "staging", "production"], var.environment)
    error_message = "Environment must be one of: development, staging, production."
  }
}

variable "node_instance_type" {
  description = "EC2 instance type for EKS worker nodes. t3.xlarge (4 vCPU, 16GB) is the minimum for running Ollama with llama3.2"
  type        = string
  default     = "t3.xlarge"
}

variable "min_nodes" {
  description = "Minimum number of worker nodes in the EKS node group. Set to 1 for cost savings in dev, 2+ for production HA"
  type        = number
  default     = 1

  validation {
    condition     = var.min_nodes >= 1
    error_message = "Minimum nodes must be at least 1."
  }
}

variable "max_nodes" {
  description = "Maximum number of worker nodes. The cluster autoscaler won't scale beyond this, even under heavy load"
  type        = number
  default     = 5

  validation {
    condition     = var.max_nodes >= 1 && var.max_nodes <= 20
    error_message = "Maximum nodes must be between 1 and 20."
  }
}
