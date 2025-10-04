
from flask import Flask
from .extensions import db, migrate, admin
from .models import WorkOrder, Vehicle, Customer
from .views import main_bp
from .admin import setup_admin
import os

def create_app():
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY="change-me",
        SQLALCHEMY_DATABASE_URI=os.getenv("DATABASE_URL", "sqlite:///local.db").replace("postgres://","postgresql://"),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )
    db.init_app(app)
    migrate.init_app(app, db)
    setup_admin(app)
    app.register_blueprint(main_bp)
    return app
