# ==============================================================================
# ContextOS — Terraform Outputs
# ==============================================================================
# These values are printed after `terraform apply` and can be referenced
# by other Terraform modules or scripts. They provide the exact values
# needed to configure kubectl, push Docker images, and connect to the cluster.
# ==============================================================================

output "cluster_endpoint" {
  description = "EKS API server endpoint URL — used by kubectl to communicate with the cluster"
  value       = aws_eks_cluster.main.endpoint
}

output "cluster_name" {
  description = "EKS cluster name — needed for aws eks update-kubeconfig"
  value       = aws_eks_cluster.main.name
}

output "cluster_version" {
  description = "Kubernetes version running on the cluster"
  value       = aws_eks_cluster.main.version
}

output "ecr_api_url" {
  description = "ECR repository URL for the API image — use as the image name in docker tag/push"
  value       = aws_ecr_repository.api.repository_url
}

output "ecr_dashboard_url" {
  description = "ECR repository URL for the dashboard image — use as the image name in docker tag/push"
  value       = aws_ecr_repository.dashboard.repository_url
}

output "s3_backup_bucket" {
  description = "S3 bucket name for database backups"
  value       = aws_s3_bucket.backups.id
}

output "s3_backup_role_arn" {
  description = "IAM role ARN for S3 backup access — annotate the Kubernetes ServiceAccount with this"
  value       = aws_iam_role.s3_backup.arn
}

output "vpc_id" {
  description = "VPC ID — useful for peering, security groups, or other Terraform modules"
  value       = aws_vpc.main.id
}

output "private_subnet_ids" {
  description = "Private subnet IDs — where EKS nodes run (no direct internet access)"
  value       = aws_subnet.private[*].id
}

output "public_subnet_ids" {
  description = "Public subnet IDs — where the ALB and NAT Gateway run"
  value       = aws_subnet.public[*].id
}

# ==============================================================================
# Helper Commands — printed for convenience
# ==============================================================================

output "kubeconfig_command" {
  description = "Run this command to configure kubectl to connect to the EKS cluster"
  value       = "aws eks update-kubeconfig --region ${var.aws_region} --name ${aws_eks_cluster.main.name}"
}

output "ecr_login_command" {
  description = "Run this command to authenticate Docker with ECR before pushing images"
  value       = "aws ecr get-login-password --region ${var.aws_region} | docker login --username AWS --password-stdin ${aws_ecr_repository.api.repository_url}"
}
