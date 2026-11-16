from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

db = SQLAlchemy()


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    account = db.Column(db.String(32), nullable=False, index=True)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    country = db.Column(db.String(2), nullable=False)
    merchant = db.Column(db.String(100), nullable=False)
    risk_score = db.Column(db.Integer, default=0, nullable=False)
    reasons = db.Column(db.String(255), default="")
    flagged = db.Column(db.Boolean, default=False, nullable=False, index=True)
    created_by = db.Column(db.String(64))
    created_at = db.Column(db.DateTime, default=utcnow, index=True)


class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True)
    action = db.Column(db.String(64), nullable=False, index=True)
    detail = db.Column(db.String(255), default="")
    ip = db.Column(db.String(64))
    created_at = db.Column(db.DateTime, default=utcnow, index=True)
