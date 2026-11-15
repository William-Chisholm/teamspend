from flask import Blueprint, jsonify
from sqlalchemy import select

from .extensions import db

bp = Blueprint("health", __name__)


@bp.get("/health")
def health():
    """Liveness plus a database connectivity check."""
    try:
        db.session.execute(select(1))
    except Exception:
        return jsonify(status="degraded", database="down"), 503
    return jsonify(status="ok", database="up")
