from flask import Flask
from flask_login import LoginManager
from flask_mail import Mail
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os

from config import config
from models.db import db
from routes import register_blueprints
from utils.helpers import setup_logging

# Extensions
login_manager = LoginManager()
mail = Mail()
limiter = Limiter(key_func=get_remote_address)

def create_app(config_name='default'):
    app = Flask(__name__)
    
    # Register os module for templates
    app.jinja_env.globals.update(os=os)

    # Load config
    app.config.from_object(config[config_name])

    # Create required folders
    os.makedirs(app.config.get('UPLOAD_FOLDER', 'static/uploads/products'), exist_ok=True)
    os.makedirs('database', exist_ok=True)
    os.makedirs('logs', exist_ok=True)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please login to access this page.'
    mail.init_app(app)
    limiter.init_app(app)

    # Register routes
    register_blueprints(app)

    # Logging
    app.logger = setup_logging()

    # Login loader
    @login_manager.user_loader
    def load_user(user_id):
        from models.user import User
        return db.session.get(User, int(user_id))

    # Database initialization
    with app.app_context():
        db.create_all()

        # Default admin
        from models.user import User
        admin = User.query.filter_by(role='admin').first()
        if not admin:
            admin = User(name='Administrator', email='admin@villagemarket.com', mobile='9999999999', role='admin', is_active=True)
            admin.set_password('Admin@123')
            db.session.add(admin)
            db.session.commit()
            print("Default admin created")

        # Default categories
        from models.product import Category
        categories = [
            ('Fresh Produce', 'fresh-produce', 'Fresh fruits and vegetables'),
            ('Dairy & Eggs', 'dairy-eggs', 'Milk, cheese, eggs and more'),
            ('Grains & Pulses', 'grains-pulses', 'Rice, wheat, lentils'),
            ('Spices', 'spices', 'Traditional spices and masalas'),
            ('Handicrafts', 'handicrafts', 'Local handicrafts and artifacts')
        ]

        for name, slug, desc in categories:
            exists = Category.query.filter_by(slug=slug).first()
            if not exists:
                category = Category(name=name, slug=slug, description=desc, is_active=True)
                db.session.add(category)
        db.session.commit()

    return app

if __name__ == '__main__':
    app = create_app(os.environ.get('FLASK_ENV', 'development'))
    app.run(host='0.0.0.0', port=5000, debug=True)
