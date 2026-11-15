import os


class Config:
    # Dev-only fallback. Production must supply SECRET_KEY via the environment.
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-change-me")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "postgresql+psycopg://teamspend:teamspend@localhost:5432/teamspend",
    )


class TestConfig(Config):
    TESTING = True
