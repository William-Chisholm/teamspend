import pytest
import sqlalchemy as sa
from sqlalchemy.engine import make_url

from app import create_app
from app.config import TestConfig
from app.extensions import db


def _ensure_test_database() -> str:
    """Create a separate <name>_test database so tests never touch dev data."""
    base_url = make_url(TestConfig.SQLALCHEMY_DATABASE_URI)
    test_name = f"{base_url.database}_test"

    admin = sa.create_engine(base_url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    try:
        with admin.connect() as conn:
            exists = conn.execute(
                sa.text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": test_name}
            ).scalar()
            if not exists:
                conn.execute(sa.text(f'CREATE DATABASE "{test_name}"'))
    finally:
        admin.dispose()

    return base_url.set(database=test_name).render_as_string(hide_password=False)


@pytest.fixture(scope="session")
def app():
    test_url = _ensure_test_database()

    class _TestConfig(TestConfig):
        SQLALCHEMY_DATABASE_URI = test_url

    app = create_app(_TestConfig)
    with app.app_context():
        db.create_all()
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def db_session(app):
    with app.app_context():
        yield db.session
        db.session.rollback()


@pytest.fixture(autouse=True)
def clean_db(app):
    """Empty every table after each test."""
    yield
    with app.app_context():
        db.session.rollback()
        for table in reversed(db.metadata.sorted_tables):
            db.session.execute(table.delete())
        db.session.commit()
