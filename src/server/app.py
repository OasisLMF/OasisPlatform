"""
Oasis API server application endpoints.
"""
from __future__ import absolute_import, unicode_literals
from flask import Flask
from flask_jwt_extended import JWTManager

from ..conf.settings import settings


def create_app(app_settings=None):
    app_settings = app_settings or {}
    if 'SQLALCHEMY_DATABASE_URI' not in app_settings:
        app_settings['SQLALCHEMY_DATABASE_URI'] = settings.get('server', 'SQLALCHEMY_DATABASE_URI')

    app = Flask(__name__)
    server_settings = {k.upper(): v for k, v in settings['server'].items()}
    app.config.update(server_settings)
    app.config.update(app_settings)

    # Database
    from .models import db
    db.init_app(app)

    # JTW
    JWTManager(app)

    # Blueprints
    from .views import root
    app.register_blueprint(root)

    return app
