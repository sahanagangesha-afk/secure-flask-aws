#!/bin/bash
# Rendered by Terraform; real work lives in deploy/setup_server.sh
set -euxo pipefail
exec > >(tee /var/log/user-data.log) 2>&1

export DEBIAN_FRONTEND=noninteractive
apt-get update -y && apt-get install -y git
git clone "${repo_url}" /opt/flaskapp

export AWS_REGION="${aws_region}"
export DB_HOST="${db_host}"
export DB_NAME="${db_name}"
export DB_USER="${db_user}"
export DB_PASSWORD_PARAM="${db_password_param}"
export SECRET_KEY_PARAM="${secret_key_param}"
export ADMIN_PASSWORD_PARAM="${admin_password_param}"
export S3_BUCKET="${s3_bucket}"
export ENABLE_STRESS_ENDPOINT="${enable_stress_endpoint}"
export COOKIE_SECURE="${cookie_secure}"

bash /opt/flaskapp/deploy/setup_server.sh
