from flask import Flask

from .config import Config
from .extensions import db, migrate
from .health import bp as health_bp


def create_app(config_object: type[Config] = Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_object)

    db.init_app(app)
    migrate.init_app(app, db)

    # Import models so Alembic autogenerate and db.create_all() can see them.
    from . import models  # noqa: F401

    app.register_blueprint(health_bp, url_prefix="/api")
    return app
