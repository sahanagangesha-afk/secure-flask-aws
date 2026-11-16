import secrets
import time
from datetime import timedelta
from functools import wraps

from flask import (Blueprint, abort, current_app, flash, jsonify, redirect,
                   render_template, request, session, url_for)
from sqlalchemy import func, text

from .audit import audit
from .fraud import is_flagged, score_transaction
from .models import AuditLog, Transaction, User, db, utcnow

bp = Blueprint("main", __name__)

MAX_FAILED_LOGINS = 5
LOCKOUT_MINUTES = 15


# ---------- helpers ----------
def csrf_token():
    if "_csrf" not in session:
        session["_csrf"] = secrets.token_hex(16)
    return session["_csrf"]


def current_user():
    uid = session.get("uid")
    return db.session.get(User, uid) if uid else None


def login_required(admin=False):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            user = current_user()
            if not user:
                return redirect(url_for("main.login"))
            if admin and not user.is_admin:
                audit("ACCESS_DENIED", user.username, request.path)
                abort(403)
            return view(*args, **kwargs)
        return wrapped
    return decorator



@bp.before_request
def verify_csrf():
    if request.method == "POST":
        submitted_token = request.form.get("_csrf", "")
        expected_token = session.get("_csrf", "")

        if (
            not submitted_token
            or not expected_token
            or not secrets.compare_digest(submitted_token, expected_token)
        ):
            abort(400, "Invalid CSRF token")



@bp.app_context_processor
def inject_globals():
    return {"csrf_token": csrf_token, "current_user": current_user()}


@bp.after_app_request
def security_headers(resp):
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "same-origin"
    resp.headers["Content-Security-Policy"] = "default-src 'self'; style-src 'self' 'unsafe-inline'"
    return resp


# ---------- health (used by ALB target group) ----------
@bp.get("/health")
def health():
    try:
        db.session.execute(text("SELECT 1"))
        return jsonify(status="ok"), 200
    except Exception:
        return jsonify(status="db-unreachable"), 503


# ---------- auth ----------
@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()[:64]
        since = utcnow() - timedelta(minutes=LOCKOUT_MINUTES)
        failures = AuditLog.query.filter(
            AuditLog.action == "LOGIN_FAILED", AuditLog.username == username,
            AuditLog.created_at >= since).count()
        if failures >= MAX_FAILED_LOGINS:
            audit("LOGIN_LOCKED", username)
            flash("Too many failed attempts. Try again later.")
            return render_template("login.html"), 429

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(request.form.get("password", "")):
            session.clear()
            session["uid"] = user.id
            session.permanent = False
            audit("LOGIN_OK", username)
            return redirect(url_for("main.dashboard"))
        audit("LOGIN_FAILED", username)
        flash("Invalid credentials.")
    return render_template("login.html")


@bp.post("/logout")
def logout():
    user = current_user()
    if user:
        audit("LOGOUT", user.username)
    session.clear()
    return redirect(url_for("main.login"))


# ---------- app ----------
@bp.get("/")
@login_required()
def dashboard():
    txns = Transaction.query.order_by(Transaction.created_at.desc()).limit(20).all()
    return render_template("dashboard.html", txns=txns)


@bp.post("/transactions")
@login_required()
def add_transaction():
    user = current_user()
    try:
        amount = round(float(request.form["amount"]), 2)
        if amount <= 0 or amount > 10_000_000:
            raise ValueError
        account = request.form["account"].strip()[:32]
        country = request.form["country"].strip().upper()[:2]
        merchant = request.form["merchant"].strip()[:100]
        if not (account and merchant and len(country) == 2):
            raise ValueError
    except (KeyError, ValueError):
        flash("Invalid transaction input.")
        return redirect(url_for("main.dashboard"))

    now = utcnow()
    recent = Transaction.query.filter(
        Transaction.account == account,
        Transaction.created_at >= now - timedelta(minutes=10)).count()
    score, reasons = score_transaction(amount, country, now.hour, recent)
    txn = Transaction(account=account, amount=amount, country=country, merchant=merchant,
                      risk_score=score, reasons=", ".join(reasons), flagged=is_flagged(score),
                      created_by=user.username)
    db.session.add(txn)
    db.session.commit()
    audit("TXN_FLAGGED" if txn.flagged else "TXN_CREATED", user.username,
          f"id={txn.id} account={account} amount={amount} score={score}")
    flash(f"Transaction recorded. Risk score {score}" + (" - FLAGGED" if txn.flagged else ""))
    return redirect(url_for("main.dashboard"))


@bp.get("/admin")
@login_required(admin=True)
def admin():
    stats = {
        "total": Transaction.query.count(),
        "flagged": Transaction.query.filter_by(flagged=True).count(),
        "volume": db.session.query(func.coalesce(func.sum(Transaction.amount), 0)).scalar(),
        "failed_logins": AuditLog.query.filter_by(action="LOGIN_FAILED").count(),
    }
    flagged = Transaction.query.filter_by(flagged=True).order_by(Transaction.created_at.desc()).limit(25).all()
    logs = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(50).all()
    return render_template("admin.html", stats=stats, flagged=flagged, logs=logs)


# ---------- demo-only load generator for Auto Scaling tests ----------
@bp.get("/stress")
def stress():
    if not current_app.config["ENABLE_STRESS_ENDPOINT"]:
        abort(404)
    seconds = min(max(float(request.args.get("seconds", 1)), 0.1), 5)
    end = time.time() + seconds
    while time.time() < end:
        sum(i * i for i in range(10_000))
    return jsonify(burned_cpu_seconds=seconds)
