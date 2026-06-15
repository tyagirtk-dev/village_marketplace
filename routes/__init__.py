from flask import Blueprint

# Import all blueprints
from routes.auth import auth_bp
from routes.main import main_bp
from routes.customer import customer_bp
from routes.seller import seller_bp
from routes.admin import admin_bp
from routes.api import api_bp


def register_blueprints(app):
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(main_bp)
    app.register_blueprint(customer_bp, url_prefix='/customer')
    app.register_blueprint(seller_bp, url_prefix='/seller')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(api_bp, url_prefix='/api')
