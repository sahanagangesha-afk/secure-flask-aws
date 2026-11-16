import logging

from flask import request

from .models import AuditLog, db

_logger = logging.getLogger("audit")


def audit(action, username=None, detail=""):
    ip = request.remote_addr if request else None
    db.session.add(AuditLog(username=username, action=action, detail=detail[:255], ip=ip))
    db.session.commit()
    _logger.info("user=%s action=%s ip=%s detail=%s", username, action, ip, detail)
