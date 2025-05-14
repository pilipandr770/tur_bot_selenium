# app/__init__.py
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask import Flask
from dotenv import load_dotenv

load_dotenv()

db = SQLAlchemy()
migrate = Migrate()

def create_app():
    app = Flask(__name__)
    app.config.from_object('app.config.Config')

    db.init_app(app)
    migrate.init_app(app, db)

    # Регистрируем модели
    with app.app_context():
        from . import models
        
    # Регистрируем блюпринт для проверки работоспособности
    from app.health import health_bp
    app.register_blueprint(health_bp, url_prefix='/')

    return app
