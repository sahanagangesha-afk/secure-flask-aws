import logging
import os
from logging.handlers import RotatingFileHandler

from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

from .models import db


def create_app(config=None):
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=os.getenv("SECRET_KEY", "dev-only-change-me"),
        SQLALCHEMY_DATABASE_URI=os.getenv("DATABASE_URL", "sqlite:///fraud.db"),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SQLALCHEMY_ENGINE_OPTIONS={"pool_pre_ping": True, "pool_recycle": 280},
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.getenv("COOKIE_SECURE", "false").lower() == "true",
        ENABLE_STRESS_ENDPOINT=os.getenv("ENABLE_STRESS_ENDPOINT", "false").lower() == "true",
        LOG_DIR=os.getenv("LOG_DIR", "logs"),
    )
    if config:
        app.config.update(config)

    # Trust X-Forwarded-* headers from Nginx / the ALB so audit logs record real client IPs.
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=2, x_proto=1, x_host=1)

    db.init_app(app)
    _setup_audit_file_logger(app)

    from .routes import bp
    from .cli import register_cli

    app.register_blueprint(bp)
    register_cli(app)
    return app


def _setup_audit_file_logger(app):
    """Audit events also go to a file that CloudWatch Logs ships off the box."""
    logger = logging.getLogger("audit")
    logger.setLevel(logging.INFO)
    if logger.handlers:
        return
    try:
        os.makedirs(app.config["LOG_DIR"], exist_ok=True)
        handler = RotatingFileHandler(
            os.path.join(app.config["LOG_DIR"], "audit.log"), maxBytes=5_000_000, backupCount=5
        )
    except OSError:
        handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
    logger.addHandler(handler)
