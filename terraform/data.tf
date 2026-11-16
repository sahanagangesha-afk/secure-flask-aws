resource "random_password" "db" {
  length  = 24
  special = false
}

resource "random_password" "secret_key" {
  length  = 48
  special = false
}

resource "random_password" "admin" {
  length  = 16
  special = false
}

resource "random_id" "suffix" {
  byte_length = 4
}

# ---------- Secrets in SSM Parameter Store (read by the EC2 role, never in git) ----------
resource "aws_ssm_parameter" "db_password" {
  name  = "/${var.project_name}/db_password"
  type  = "SecureString"
  value = random_password.db.result
}

resource "aws_ssm_parameter" "secret_key" {
  name  = "/${var.project_name}/secret_key"
  type  = "SecureString"
  value = random_password.secret_key.result
}

resource "aws_ssm_parameter" "admin_password" {
  name  = "/${var.project_name}/admin_password"
  type  = "SecureString"
  value = random_password.admin.result
}

# ---------- RDS MySQL in private subnets ----------
resource "aws_db_subnet_group" "main" {
  name       = "${var.project_name}-db-subnets"
  subnet_ids = aws_subnet.private[*].id
}

resource "aws_db_instance" "main" {
  identifier              = "${var.project_name}-mysql"
  engine                  = "mysql"
  engine_version          = "8.0"
  instance_class          = var.db_instance_class
  allocated_storage       = 20
  db_name                 = "frauddb"
  username                = "fraudadmin"
  password                = random_password.db.result
  db_subnet_group_name    = aws_db_subnet_group.main.name
  vpc_security_group_ids  = [aws_security_group.db.id]
  publicly_accessible     = false
  storage_encrypted       = true
  backup_retention_period = 7
  multi_az                = false # set true for production HA (doubles RDS cost)
  skip_final_snapshot     = true  # demo setting; use a final snapshot in production
  deletion_protection     = false
}

# ---------- S3 for backups & logs ----------
resource "aws_s3_bucket" "backups" {
  bucket = "${var.project_name}-backups-${random_id.suffix.hex}"
}

resource "aws_s3_bucket_public_access_block" "backups" {
  bucket                  = aws_s3_bucket.backups.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "backups" {
  bucket = aws_s3_bucket.backups.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "backups" {
  bucket = aws_s3_bucket.backups.id
  rule {
    apply_server_side_encryption_by_default { sse_algorithm = "AES256" }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "backups" {
  bucket = aws_s3_bucket.backups.id
  rule {
    id     = "expire-old-backups"
    status = "Enabled"
    filter { prefix = "db-backups/" }
    expiration { days = 30 }
    noncurrent_version_expiration { noncurrent_days = 7 }
  }
}
