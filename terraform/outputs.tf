output "app_url" {
  value = "http://${aws_lb.web.dns_name}"
}

output "backup_bucket" {
  value = aws_s3_bucket.backups.bucket
}

output "rds_endpoint" {
  value = aws_db_instance.main.address
}

output "get_admin_password_cmd" {
  value = "aws ssm get-parameter --name ${aws_ssm_parameter.admin_password.name} --with-decryption --query Parameter.Value --output text --region ${var.aws_region}"
}
