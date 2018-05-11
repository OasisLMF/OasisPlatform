"""
Oasis API server application endpoints.
"""
from __future__ import absolute_import, unicode_literals
from flask import Flask

from ..conf.settings import settings


def create_app(database_uri=None, track_modifications=True):
    if database_uri is None:
        database_uri = settings.get('server', 'SQLALCHEMY_DATABASE_URI')

    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = database_uri
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = track_modifications

    # Database
    from .models import db
    db.init_app(app)

    # Blueprints
    from .views import root
    app.register_blueprint(root)

    return app
