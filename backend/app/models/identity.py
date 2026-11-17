import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from ..extensions import db
from .base import CreatedAtMixin, TenantMixin, UUIDPrimaryKeyMixin, enum_type
from .enums import Role


class User(UUIDPrimaryKeyMixin, CreatedAtMixin, db.Model):
    __tablename__ = "users"

    # Store emails lowercased (normalize in the service layer).
    email: Mapped[str] = mapped_column(sa.String(320), unique=True)
    password_hash: Mapped[str] = mapped_column(sa.String(255))
    name: Mapped[str] = mapped_column(sa.String(200))


class Organization(UUIDPrimaryKeyMixin, CreatedAtMixin, db.Model):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(sa.String(200))
    slug: Mapped[str] = mapped_column(sa.String(63), unique=True)


class Membership(UUIDPrimaryKeyMixin, CreatedAtMixin, db.Model):
    """A user's role within one org. Roles are per membership, never global."""

    __tablename__ = "memberships"
    __table_args__ = (
        sa.UniqueConstraint("user_id", "org_id", name="uq_memberships_user_id_org_id"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(sa.ForeignKey("users.id", ondelete="CASCADE"))
    org_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[Role] = mapped_column(enum_type(Role, "membership_role"))


class Invite(UUIDPrimaryKeyMixin, CreatedAtMixin, TenantMixin, db.Model):
    __tablename__ = "invites"

    email: Mapped[str] = mapped_column(sa.String(320))
    role: Mapped[Role] = mapped_column(enum_type(Role, "invite_role"))
    # SHA-256 hex digest of the token. The raw token is never stored.
    token_hash: Mapped[str] = mapped_column(sa.String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True))
    accepted_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        sa.ForeignKey("users.id", ondelete="SET NULL")
    )
