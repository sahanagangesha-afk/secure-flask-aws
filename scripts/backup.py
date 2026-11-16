"""Back up the database to S3. Uses the EC2 IAM role (no access keys).

Usage:  python scripts/backup.py        (needs S3_BUCKET, DATABASE_URL, AWS_REGION in env)
"""
import datetime
import gzip
import os
import shutil
import subprocess
import tempfile
from urllib.parse import urlparse

import boto3


def main():
    bucket = os.environ["S3_BUCKET"]
    url = urlparse(os.environ["DATABASE_URL"])
    stamp = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    tmpdir = tempfile.mkdtemp()
    out = os.path.join(tmpdir, f"backup-{stamp}.sql.gz")

    if url.scheme.startswith("mysql"):
        env = dict(os.environ, MYSQL_PWD=url.password or "")
        dump = subprocess.run(
            ["mysqldump", "--single-transaction", "-h", url.hostname, "-u", url.username, url.path.lstrip("/")],
            check=True, capture_output=True, env=env)
        with gzip.open(out, "wb") as f:
            f.write(dump.stdout)
    else:  # SQLite (local/dev)
        out = out.replace(".sql.gz", ".db.gz")
        with open(url.path.lstrip("/") or "instance/fraud.db", "rb") as src, gzip.open(out, "wb") as dst:
            shutil.copyfileobj(src, dst)

    key = f"db-backups/{os.path.basename(out)}"
    boto3.client("s3").upload_file(out, bucket, key, ExtraArgs={"ServerSideEncryption": "AES256"})
    print(f"Uploaded s3://{bucket}/{key}")
    shutil.rmtree(tmpdir)


if __name__ == "__main__":
    main()
