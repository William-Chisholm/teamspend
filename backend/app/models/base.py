import enum
import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, declared_attr, mapped_column


class UUIDPrimaryKeyMixin:
    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, primary_key=True, default=uuid.uuid4)


class CreatedAtMixin:
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now()
    )


class TimestampMixin(CreatedAtMixin):
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
        onupdate=sa.func.now(),
    )


class TenantMixin:
    """Marks a model as tenant-scoped.

    Every model using this mixin gets a non-null, indexed ``org_id`` foreign key.
    The tenant-scoping hook (P2) keys off this mixin: it automatically filters
    ORM queries on these models by the current request's org, and rejects writes
    whose ``org_id`` doesn't match.

    Deliberately NOT applied to ``Membership``: it carries an ``org_id`` but is
    also read by ``user_id`` during login and org listing, so it is only ever
    queried through the explicit ``unscoped()`` helper in ``auth/`` and
    ``tenancy/``.
    """

    @declared_attr
    def org_id(cls) -> Mapped[uuid.UUID]:
        return mapped_column(
            sa.Uuid,
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            index=True,
        )


def enum_type(enum_cls: type[enum.Enum], name: str) -> sa.Enum:
    """Store a Python enum as VARCHAR plus a named CHECK constraint.

    Native Postgres enums are painful to alter in migrations, so we trade a
    little storage for easier schema changes. The DB still rejects bad values.
    """
    return sa.Enum(
        enum_cls,
        name=name,
        native_enum=False,
        length=20,
        create_constraint=True,
        validate_strings=True,
        values_callable=lambda e: [member.value for member in e],
    )
