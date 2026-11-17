import uuid

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ..extensions import db
from .base import CreatedAtMixin, TenantMixin, UUIDPrimaryKeyMixin

# JSONB on Postgres, plain JSON elsewhere.
JSONType = sa.JSON().with_variant(JSONB(), "postgresql")


class AuditLog(UUIDPrimaryKeyMixin, CreatedAtMixin, TenantMixin, db.Model):
    __tablename__ = "audit_log"
    __table_args__ = (sa.Index("ix_audit_log_org_created", "org_id", "created_at"),)

    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.ForeignKey("users.id", ondelete="SET NULL")
    )
    action: Mapped[str] = mapped_column(sa.String(100))
    entity_type: Mapped[str] = mapped_column(sa.String(50))
    entity_id: Mapped[uuid.UUID | None] = mapped_column()
    diff_json: Mapped[dict | None] = mapped_column(JSONType)
