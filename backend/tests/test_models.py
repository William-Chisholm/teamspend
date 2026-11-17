from datetime import date

import pytest
from sqlalchemy.exc import IntegrityError

from app.models import Category, Expense, Membership, Organization, Role, User
from app.models.base import TenantMixin


def make_org(session, slug):
    org = Organization(name=slug, slug=slug)
    session.add(org)
    session.flush()
    return org


def make_user(session, email):
    user = User(email=email, password_hash="x", name="Test User")
    session.add(user)
    session.flush()
    return user


def make_category(session, org, name="Travel"):
    category = Category(org_id=org.id, name=name)
    session.add(category)
    session.flush()
    return category


def make_expense(session, org, user, category, amount_cents=1000):
    expense = Expense(
        org_id=org.id,
        submitted_by=user.id,
        category_id=category.id,
        amount_cents=amount_cents,
        expense_date=date(2026, 11, 16),
    )
    session.add(expense)
    session.flush()
    return expense


def test_tenant_mixin_models_have_non_nullable_org_id():
    # The scoping hook (P2) relies on exactly these models carrying org_id.
    tenant_models = TenantMixin.__subclasses__()
    assert {m.__tablename__ for m in tenant_models} == {
        "audit_log",
        "categories",
        "expense_events",
        "expenses",
        "invites",
    }
    for model in tenant_models:
        assert model.__table__.c.org_id.nullable is False


def test_expense_defaults(db_session):
    org = make_org(db_session, "acme")
    user = make_user(db_session, "a@example.com")
    expense = make_expense(db_session, org, user, make_category(db_session, org))
    db_session.refresh(expense)
    assert expense.status.value == "draft"
    assert expense.currency == "USD"


def test_membership_is_unique_per_user_and_org(db_session):
    org = make_org(db_session, "acme")
    user = make_user(db_session, "a@example.com")
    db_session.add(Membership(user_id=user.id, org_id=org.id, role=Role.MEMBER))
    db_session.flush()

    db_session.add(Membership(user_id=user.id, org_id=org.id, role=Role.ADMIN))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_expense_amount_must_be_positive(db_session):
    org = make_org(db_session, "acme")
    user = make_user(db_session, "a@example.com")
    category = make_category(db_session, org)
    with pytest.raises(IntegrityError):
        make_expense(db_session, org, user, category, amount_cents=0)


def test_expense_category_must_belong_to_same_org(db_session):
    org_a = make_org(db_session, "org-a")
    org_b = make_org(db_session, "org-b")
    user = make_user(db_session, "a@example.com")
    category_b = make_category(db_session, org_b)
    with pytest.raises(IntegrityError):
        make_expense(db_session, org_a, user, category_b)
