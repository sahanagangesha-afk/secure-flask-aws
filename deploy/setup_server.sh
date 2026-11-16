#!/usr/bin/env bash
# Automates Ubuntu 22.04 server setup: hardening, Gunicorn + Nginx, CloudWatch agent, S3 backup cron.
# Run as root. Used by Terraform user_data, or manually:
#   sudo REPO_URL=https://github.com/you/repo.git bash deploy/setup_server.sh
# Optional env (set by Terraform): DB_HOST DB_NAME DB_USER DB_PASSWORD_PARAM SECRET_KEY_PARAM
#   ADMIN_PASSWORD_PARAM S3_BUCKET AWS_REGION ENABLE_STRESS_ENDPOINT
# Without DB_HOST the app falls back to SQLite (handy for the very first EC2 test).
set -euo pipefail

APP_DIR=/opt/flaskapp
LOG_DIR=/var/log/flaskapp
AWS_REGION="${AWS_REGION:-ap-south-1}"
export AWS_REGION

echo "==> System updates & packages"
export DEBIAN_FRONTEND=noninteractive
apt-get update -y && apt-get upgrade -y
apt-get install -y python3-venv python3-pip nginx ufw fail2ban unattended-upgrades git curl wget mysql-client

echo "==> Non-root service user"
id flaskapp &>/dev/null || useradd --system --home "$APP_DIR" --shell /usr/sbin/nologin flaskapp

echo "==> Firewall (ufw) + fail2ban"
ufw default deny incoming && ufw default allow outgoing
ufw allow OpenSSH && ufw allow 'Nginx Full'
ufw --force enable
systemctl enable --now fail2ban
dpkg-reconfigure -f noninteractive unattended-upgrades

echo "==> App code"
if [ ! -d "$APP_DIR/.git" ]; then
  : "${REPO_URL:?Set REPO_URL to your GitHub repo}"
  git clone "$REPO_URL" "$APP_DIR"
fi
mkdir -p "$LOG_DIR" "$APP_DIR/instance"
python3 -m venv "$APP_DIR/venv"
"$APP_DIR/venv/bin/pip" install --upgrade pip -q
"$APP_DIR/venv/bin/pip" install -r "$APP_DIR/requirements.txt" -q

get_param() {  # fetch a SecureString from SSM Parameter Store using the instance's IAM role
  PARAM="$1" "$APP_DIR/venv/bin/python" -c \
   "import boto3,os;print(boto3.client('ssm').get_parameter(Name=os.environ['PARAM'],WithDecryption=True)['Parameter']['Value'])"
}

echo "==> Environment file (no secrets in git)"
SECRET_KEY="$( [ -n "${SECRET_KEY_PARAM:-}" ] && get_param "$SECRET_KEY_PARAM" || openssl rand -hex 32 )"
ADMIN_PASSWORD="$( [ -n "${ADMIN_PASSWORD_PARAM:-}" ] && get_param "$ADMIN_PASSWORD_PARAM" || true )"
if [ -n "${DB_HOST:-}" ]; then
  DB_PASSWORD="$(get_param "$DB_PASSWORD_PARAM")"
  DATABASE_URL="mysql+pymysql://${DB_USER}:${DB_PASSWORD}@${DB_HOST}/${DB_NAME}"
else
  DATABASE_URL="sqlite:////opt/flaskapp/instance/fraud.db"
fi
cat > /etc/flaskapp.env <<ENVEOF
SECRET_KEY=$SECRET_KEY
DATABASE_URL=$DATABASE_URL
ADMIN_PASSWORD=$ADMIN_PASSWORD
LOG_DIR=$LOG_DIR
S3_BUCKET=${S3_BUCKET:-}
AWS_REGION=$AWS_REGION
ENABLE_STRESS_ENDPOINT=${ENABLE_STRESS_ENDPOINT:-false}
COOKIE_SECURE=${COOKIE_SECURE:-false}
ENVEOF
chown root:flaskapp /etc/flaskapp.env && chmod 640 /etc/flaskapp.env
chown -R flaskapp:flaskapp "$LOG_DIR" "$APP_DIR/instance"

echo "==> Initialise database"
set -a; . /etc/flaskapp.env; set +a
(cd "$APP_DIR" && sudo -E -u flaskapp "$APP_DIR/venv/bin/flask" --app wsgi init-db)

echo "==> systemd + Nginx"
cp "$APP_DIR/deploy/flaskapp.service" /etc/systemd/system/flaskapp.service
cp "$APP_DIR/deploy/nginx.conf" /etc/nginx/sites-available/flaskapp
ln -sf /etc/nginx/sites-available/flaskapp /etc/nginx/sites-enabled/flaskapp
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl daemon-reload
systemctl enable --now flaskapp
systemctl restart nginx

echo "==> CloudWatch agent (memory, disk, logs)"
wget -q https://amazoncloudwatch-agent.s3.amazonaws.com/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb -O /tmp/cw.deb
dpkg -i /tmp/cw.deb
/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl -a fetch-config -m ec2 -s \
  -c file:"$APP_DIR/deploy/cloudwatch-agent.json"

if [ -n "${S3_BUCKET:-}" ]; then
  echo "==> Nightly DB backup to S3 (02:30)"
  cat > /etc/cron.d/flaskapp-backup <<CRONEOF
30 2 * * * flaskapp set -a; . /etc/flaskapp.env; set +a; cd $APP_DIR && $APP_DIR/venv/bin/python scripts/backup.py >> $LOG_DIR/backup.log 2>&1
CRONEOF
fi
echo "==> Done."
