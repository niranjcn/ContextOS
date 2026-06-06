# ==============================================================================
# ContextOS — Terraform Main Configuration (AWS)
# ==============================================================================
# Creates the complete AWS infrastructure for running ContextOS in production:
#   1. VPC with public/private subnets (network isolation)
#   2. EKS cluster with managed node group (Kubernetes)
#   3. ECR repositories (Docker image registry)
#   4. S3 bucket for backups (with encryption and lifecycle policies)
#   5. IAM roles and policies (least-privilege access)
#
# Usage:
#   cd terraform
#   terraform init      # Download AWS provider
#   terraform plan      # Preview what will be created
#   terraform apply     # Create everything
#   terraform destroy   # Tear everything down
# ==============================================================================

terraform {
  required_version = ">= 1.5.0"

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

  # RECOMMENDED: Uncomment this block and configure a remote S3 backend
  # to store Terraform state. Without it, state is stored locally and
  # can be lost if your laptop dies.
  #
  # backend "s3" {
  #   bucket         = "contextos-terraform-state"
  #   key            = "production/terraform.tfstate"
  #   region         = "us-east-1"
  #   encrypt        = true
  #   dynamodb_table = "terraform-lock"  # Prevents concurrent applies
  # }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "ContextOS"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}

# Random suffix for globally unique S3 bucket names
resource "random_id" "suffix" {
  byte_length = 4
}

# ==============================================================================
# DATA SOURCES — Look up available AZs in the selected region
# ==============================================================================

data "aws_availability_zones" "available" {
  state = "available"
}

# ==============================================================================
# 1. VPC — Network Isolation
# ==============================================================================
# The VPC is the foundation of network security. EKS nodes run in private
# subnets (no direct internet access), and only the load balancer sits in
# public subnets.

resource "aws_vpc" "main" {
  cidr_block = "10.0.0.0/16"

  # Required for EKS — the control plane needs DNS resolution to work
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = {
    Name = "${var.cluster_name}-vpc"
  }
}

# --------------------------------------------------------------------------
# Public Subnets — For the ALB (Load Balancer) and NAT Gateway
# --------------------------------------------------------------------------
# These subnets have a route to the Internet Gateway, so resources here
# can be reached from the internet. Only the load balancer goes here.

resource "aws_subnet" "public" {
  count = 2

  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.${count.index + 1}.0/24"  # 10.0.1.0/24, 10.0.2.0/24
  availability_zone = data.aws_availability_zones.available.names[count.index]

  # Auto-assign public IPs to instances launched here (needed for ALB)
  map_public_ip_on_launch = true

  tags = {
    Name = "${var.cluster_name}-public-${count.index + 1}"
    # These tags tell the AWS Load Balancer Controller to use these subnets
    "kubernetes.io/role/elb"                    = "1"
    "kubernetes.io/cluster/${var.cluster_name}" = "shared"
  }
}

# --------------------------------------------------------------------------
# Private Subnets — For EKS Worker Nodes
# --------------------------------------------------------------------------
# No direct internet access. Nodes reach the internet through the NAT Gateway.
# This prevents anyone from directly connecting to your nodes.

resource "aws_subnet" "private" {
  count = 2

  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.${count.index + 10}.0/24"  # 10.0.10.0/24, 10.0.11.0/24
  availability_zone = data.aws_availability_zones.available.names[count.index]

  tags = {
    Name = "${var.cluster_name}-private-${count.index + 1}"
    # Tell the Load Balancer Controller these are internal subnets
    "kubernetes.io/role/internal-elb"            = "1"
    "kubernetes.io/cluster/${var.cluster_name}" = "shared"
  }
}

# --------------------------------------------------------------------------
# Internet Gateway — Connects the VPC to the public internet
# --------------------------------------------------------------------------
resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name = "${var.cluster_name}-igw"
  }
}

# --------------------------------------------------------------------------
# NAT Gateway — Allows private subnets to reach the internet (outbound only)
# --------------------------------------------------------------------------
# Needed so EKS nodes can pull Docker images from ECR and download packages.
# Inbound connections from the internet are NOT allowed through NAT.

# Elastic IP for the NAT Gateway (static IP that doesn't change)
resource "aws_eip" "nat" {
  domain = "vpc"

  tags = {
    Name = "${var.cluster_name}-nat-eip"
  }
}

resource "aws_nat_gateway" "main" {
  allocation_id = aws_eip.nat.id
  subnet_id     = aws_subnet.public[0].id  # NAT Gateway lives in a public subnet

  tags = {
    Name = "${var.cluster_name}-nat"
  }

  # NAT Gateway needs the IGW to exist first
  depends_on = [aws_internet_gateway.main]
}

# --------------------------------------------------------------------------
# Route Tables — Control traffic flow
# --------------------------------------------------------------------------

# Public route table — routes internet traffic through the Internet Gateway
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"       # All internet-bound traffic
    gateway_id = aws_internet_gateway.main.id
  }

  tags = {
    Name = "${var.cluster_name}-public-rt"
  }
}

# Associate public subnets with the public route table
resource "aws_route_table_association" "public" {
  count = 2

  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

# Private route table — routes internet traffic through the NAT Gateway
resource "aws_route_table" "private" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block     = "0.0.0.0/0"   # All internet-bound traffic
    nat_gateway_id = aws_nat_gateway.main.id  # Goes through NAT, not IGW
  }

  tags = {
    Name = "${var.cluster_name}-private-rt"
  }
}

# Associate private subnets with the private route table
resource "aws_route_table_association" "private" {
  count = 2

  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private.id
}

# ==============================================================================
# 2. EKS CLUSTER — Managed Kubernetes
# ==============================================================================

# --------------------------------------------------------------------------
# IAM Role for the EKS Cluster (control plane)
# --------------------------------------------------------------------------
resource "aws_iam_role" "eks_cluster" {
  name = "${var.cluster_name}-cluster-role"

  # Trust policy — allows the EKS service to assume this role
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "eks.amazonaws.com"
      }
    }]
  })
}

# Attach the AWS-managed EKS cluster policy (provides permissions the
# EKS control plane needs to manage your cluster)
resource "aws_iam_role_policy_attachment" "eks_cluster_policy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy"
  role       = aws_iam_role.eks_cluster.name
}

# Security group for the EKS cluster
resource "aws_security_group" "eks_cluster" {
  name_prefix = "${var.cluster_name}-cluster-"
  vpc_id      = aws_vpc.main.id

  # Allow all outbound traffic (nodes need to reach ECR, etc.)
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.cluster_name}-cluster-sg"
  }
}

# The EKS cluster itself
resource "aws_eks_cluster" "main" {
  name     = var.cluster_name
  version  = "1.29"
  role_arn = aws_iam_role.eks_cluster.arn

  vpc_config {
    subnet_ids = concat(
      aws_subnet.public[*].id,
      aws_subnet.private[*].id
    )
    security_group_ids      = [aws_security_group.eks_cluster.id]
    endpoint_private_access = true   # Nodes can reach the API server internally
    endpoint_public_access  = true   # You can run kubectl from your laptop
  }

  # Enable OIDC provider for IAM Roles for Service Accounts (IRSA).
  # This lets individual pods assume specific IAM roles instead of
  # giving the entire node broad permissions.

  depends_on = [
    aws_iam_role_policy_attachment.eks_cluster_policy,
  ]

  tags = {
    Name = var.cluster_name
  }
}

# OIDC provider — enables IRSA (IAM Roles for Service Accounts)
data "aws_iam_openid_connect_provider" "eks" {
  url = aws_eks_cluster.main.identity[0].oidc[0].issuer

  depends_on = [aws_eks_cluster.main]
}

# Create the OIDC provider if it doesn't exist
resource "aws_iam_openid_connect_provider" "eks" {
  url = aws_eks_cluster.main.identity[0].oidc[0].issuer

  client_id_list = ["sts.amazonaws.com"]

  # Thumbprint for the OIDC issuer — AWS requires this
  thumbprint_list = ["9e99a48a9960b14926bb7f3b02e22da2b0ab7280"]

  tags = {
    Name = "${var.cluster_name}-oidc"
  }
}

# --------------------------------------------------------------------------
# IAM Role for EKS Node Group (worker nodes)
# --------------------------------------------------------------------------
resource "aws_iam_role" "eks_nodes" {
  name = "${var.cluster_name}-node-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ec2.amazonaws.com"
      }
    }]
  })
}

# Worker nodes need these policies to function:
# - EKSWorkerNodePolicy: core node operations
# - EKS_CNI_Policy: networking (VPC CNI plugin)
# - EC2ContainerRegistryReadOnly: pull images from ECR
resource "aws_iam_role_policy_attachment" "eks_worker_node" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy"
  role       = aws_iam_role.eks_nodes.name
}

resource "aws_iam_role_policy_attachment" "eks_cni" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy"
  role       = aws_iam_role.eks_nodes.name
}

resource "aws_iam_role_policy_attachment" "ecr_read" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
  role       = aws_iam_role.eks_nodes.name
}

# --------------------------------------------------------------------------
# EKS Managed Node Group — Worker EC2 instances
# --------------------------------------------------------------------------
resource "aws_eks_node_group" "main" {
  cluster_name    = aws_eks_cluster.main.name
  node_group_name = "${var.cluster_name}-nodes"
  node_role_arn   = aws_iam_role.eks_nodes.arn

  # Place nodes in private subnets only (no direct internet access)
  subnet_ids = aws_subnet.private[*].id

  # t3.xlarge: 4 vCPUs, 16GB RAM — needed for Ollama to load LLM models.
  # Smaller instances would OOM when loading even small models.
  instance_types = [var.node_instance_type]

  scaling_config {
    min_size     = var.min_nodes
    max_size     = var.max_nodes
    desired_size = 2  # Start with 2 nodes for HA
  }

  # Graceful updates — replaces nodes one at a time with a 15-minute timeout
  update_config {
    max_unavailable = 1
  }

  depends_on = [
    aws_iam_role_policy_attachment.eks_worker_node,
    aws_iam_role_policy_attachment.eks_cni,
    aws_iam_role_policy_attachment.ecr_read,
  ]

  tags = {
    Name = "${var.cluster_name}-node"
  }
}

# ==============================================================================
# 3. ECR — Docker Image Repositories
# ==============================================================================
# ECR (Elastic Container Registry) is AWS's Docker Hub. CI/CD pushes images
# here, and EKS nodes pull from here. Using ECR instead of Docker Hub is
# faster (same AWS network) and avoids Docker Hub rate limits.

resource "aws_ecr_repository" "api" {
  name                 = "contextos-api"
  image_tag_mutability = "MUTABLE"  # Allows overwriting "latest" tag

  # Scan images for CVEs on every push
  image_scanning_configuration {
    scan_on_push = true
  }

  # Encrypt images at rest with AWS-managed keys (free)
  encryption_configuration {
    encryption_type = "AES256"
  }

  tags = {
    Name = "contextos-api"
  }
}

resource "aws_ecr_repository" "dashboard" {
  name                 = "contextos-dashboard"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "AES256"
  }

  tags = {
    Name = "contextos-dashboard"
  }
}

# Lifecycle policies — automatically delete old images to save storage costs.
# Keeps the 20 most recent images and deletes untagged images after 7 days.
resource "aws_ecr_lifecycle_policy" "api" {
  repository = aws_ecr_repository.api.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Delete untagged images after 7 days"
        selection = {
          tagStatus   = "untagged"
          countType   = "sinceImagePushed"
          countUnit   = "days"
          countNumber = 7
        }
        action = {
          type = "expire"
        }
      },
      {
        rulePriority = 2
        description  = "Keep only the 20 most recent images"
        selection = {
          tagStatus   = "any"
          countType   = "imageCountMoreThan"
          countNumber = 20
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}

resource "aws_ecr_lifecycle_policy" "dashboard" {
  repository = aws_ecr_repository.dashboard.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Delete untagged images after 7 days"
        selection = {
          tagStatus   = "untagged"
          countType   = "sinceImagePushed"
          countUnit   = "days"
          countNumber = 7
        }
        action = {
          type = "expire"
        }
      },
      {
        rulePriority = 2
        description  = "Keep only the 20 most recent images"
        selection = {
          tagStatus   = "any"
          countType   = "imageCountMoreThan"
          countNumber = 20
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}

# ==============================================================================
# 4. S3 BUCKET — Data Backups
# ==============================================================================
# Stores ChromaDB and Kuzu database backups. Versioning means you can
# recover from accidental deletions. Lifecycle rules move old backups
# to Glacier (90% cheaper) after 90 days.

resource "aws_s3_bucket" "backups" {
  bucket = "contextos-data-backup-${random_id.suffix.hex}"

  # Prevent accidental deletion of the backup bucket
  # Remove this line if you need to destroy the bucket with Terraform
  force_destroy = false

  tags = {
    Name = "contextos-data-backup"
  }
}

# Enable versioning — keeps all previous versions of every object
resource "aws_s3_bucket_versioning" "backups" {
  bucket = aws_s3_bucket.backups.id

  versioning_configuration {
    status = "Enabled"
  }
}

# Server-side encryption — all objects are encrypted at rest
resource "aws_s3_bucket_server_side_encryption_configuration" "backups" {
  bucket = aws_s3_bucket.backups.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"  # Free, AWS-managed encryption
    }
    bucket_key_enabled = true   # Reduces KMS API costs if you switch to KMS later
  }
}

# Block all public access — backup data should never be public
resource "aws_s3_bucket_public_access_block" "backups" {
  bucket = aws_s3_bucket.backups.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Lifecycle rule — move old backups to Glacier after 90 days
# Glacier storage is ~$0.004/GB/month vs $0.023/GB for S3 Standard
resource "aws_s3_bucket_lifecycle_configuration" "backups" {
  bucket = aws_s3_bucket.backups.id

  rule {
    id     = "archive-old-backups"
    status = "Enabled"

    transition {
      days          = 90
      storage_class = "GLACIER"
    }

    # Delete Glacier archives after 365 days (adjust as needed)
    expiration {
      days = 365
    }

    # Also clean up old versions
    noncurrent_version_transition {
      noncurrent_days = 30
      storage_class   = "GLACIER"
    }

    noncurrent_version_expiration {
      noncurrent_days = 90
    }
  }
}

# ==============================================================================
# 5. IAM — S3 Backup Role for API Pods (IRSA)
# ==============================================================================
# This role can be assumed by the API pods (via IRSA) to write backups to S3.
# It follows the principle of least privilege — only S3 access, only to
# the backup bucket, and only the specific actions needed.

resource "aws_iam_role" "s3_backup" {
  name = "${var.cluster_name}-s3-backup-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRoleWithWebIdentity"
      Effect = "Allow"
      Principal = {
        Federated = aws_iam_openid_connect_provider.eks.arn
      }
      Condition = {
        StringEquals = {
          "${replace(aws_eks_cluster.main.identity[0].oidc[0].issuer, "https://", "")}:sub" = "system:serviceaccount:contextos:contextos-api"
        }
      }
    }]
  })
}

resource "aws_iam_role_policy" "s3_backup" {
  name = "${var.cluster_name}-s3-backup-policy"
  role = aws_iam_role.s3_backup.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "s3:PutObject",
        "s3:GetObject",
        "s3:ListBucket",
        "s3:DeleteObject"
      ]
      Resource = [
        aws_s3_bucket.backups.arn,
        "${aws_s3_bucket.backups.arn}/*"
      ]
    }]
  })
}
