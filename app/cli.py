import os
import secrets

import click

from .models import User, db


def register_cli(app):
    @app.cli.command("init-db")
    def init_db():
        """Create tables and the initial admin user (idempotent)."""
        db.create_all()
        if not User.query.filter_by(username="admin").first():
            password = os.getenv("ADMIN_PASSWORD") or secrets.token_urlsafe(12)
            admin = User(username="admin", is_admin=True)
            admin.set_password(password)
            db.session.add(admin)
            db.session.commit()
            if not os.getenv("ADMIN_PASSWORD"):
                click.echo(f"Generated admin password: {password}")
        click.echo("Database ready.")
