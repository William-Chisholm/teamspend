import uuid
from datetime import date

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from ..extensions import db
from .base import CreatedAtMixin, TenantMixin, TimestampMixin, UUIDPrimaryKeyMixin, enum_type
from .enums import ExpenseStatus


class Category(UUIDPrimaryKeyMixin, CreatedAtMixin, TenantMixin, db.Model):
    __tablename__ = "categories"
    __table_args__ = (
        sa.UniqueConstraint("org_id", "name", name="uq_categories_org_id_name"),
        # Target for composite foreign keys that force same-org references.
        sa.UniqueConstraint("org_id", "id", name="uq_categories_org_id_id"),
    )

    name: Mapped[str] = mapped_column(sa.String(100))


class Expense(UUIDPrimaryKeyMixin, TimestampMixin, TenantMixin, db.Model):
    __tablename__ = "expenses"
    __table_args__ = (
        sa.UniqueConstraint("org_id", "id", name="uq_expenses_org_id_id"),
        sa.CheckConstraint("amount_cents > 0", name="amount_positive"),
        # Defense in depth: the database itself refuses a category from another org.
        sa.ForeignKeyConstraint(["org_id", "category_id"], ["categories.org_id", "categories.id"]),
        sa.Index("ix_expenses_org_status_created", "org_id", "status", "created_at"),
    )

    submitted_by: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    category_id: Mapped[uuid.UUID] = mapped_column()
    amount_cents: Mapped[int] = mapped_column(sa.BigInteger)
    currency: Mapped[str] = mapped_column(sa.String(3), default="USD", server_default="USD")
    description: Mapped[str] = mapped_column(sa.Text, default="", server_default="")
    expense_date: Mapped[date] = mapped_column(sa.Date)
    status: Mapped[ExpenseStatus] = mapped_column(
        enum_type(ExpenseStatus, "expense_status"),
        default=ExpenseStatus.DRAFT,
        server_default=ExpenseStatus.DRAFT.value,
    )
    receipt_key: Mapped[str | None] = mapped_column(sa.String(500))


class ExpenseEvent(UUIDPrimaryKeyMixin, CreatedAtMixin, TenantMixin, db.Model):
    """One row per status transition. The auditable history of the state machine."""

    __tablename__ = "expense_events"
    __table_args__ = (
        sa.ForeignKeyConstraint(
            ["org_id", "expense_id"],
            ["expenses.org_id", "expenses.id"],
            ondelete="CASCADE",
        ),
        sa.Index("ix_expense_events_org_expense", "org_id", "expense_id"),
    )

    expense_id: Mapped[uuid.UUID] = mapped_column()
    actor_id: Mapped[uuid.UUID] = mapped_column(sa.ForeignKey("users.id", ondelete="RESTRICT"))
    from_status: Mapped[ExpenseStatus | None] = mapped_column(
        enum_type(ExpenseStatus, "event_from_status")
    )
    to_status: Mapped[ExpenseStatus] = mapped_column(enum_type(ExpenseStatus, "event_to_status"))
    comment: Mapped[str | None] = mapped_column(sa.Text)
