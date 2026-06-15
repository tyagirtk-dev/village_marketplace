from flask import Flask
from flask_login import LoginManager
from flask_mail import Mail
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from config import config
from models.db import db
from routes import register_blueprints
from utils.helpers import setup_logging
import os

# Initialize extensions
login_manager = LoginManager()
mail = Mail()
limiter = Limiter(get_remote_address)


def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Ensure instance folders
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs('database', exist_ok=True)
    os.makedirs('logs', exist_ok=True)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please login to access this page.'
    mail.init_app(app)
    limiter.init_app(app)

    # Register blueprints
    register_blueprints(app)

    # Setup logging
    logger = setup_logging()
    app.logger = logger

    @login_manager.user_loader
    def load_user(user_id):
        from models.user import User
        return User.query.get(int(user_id))

    # Create tables
    with app.app_context():
        db.create_all()

        # Create default admin if not exists
        from models.user import User
        admin = User.query.filter_by(role='admin').first()
        if not admin:
            admin = User(
                name='Administrator',
                email='admin@villagemarket.com',
                mobile='9999999999',
                role='admin',
                is_active=True
            )
            admin.set_password('Admin@123')
            db.session.add(admin)
            db.session.commit()
            print("Default admin created: admin@villagemarket.com / Admin@123")

        # Create default categories
        from models.product import Category
        default_categories = [
            ('Fresh Produce', 'fresh-produce', 'Fresh fruits and vegetables'),
            ('Dairy & Eggs', 'dairy-eggs', 'Milk, cheese, eggs and more'),
            ('Grains & Pulses', 'grains-pulses', 'Rice, wheat, lentils'),
            ('Spices', 'spices', 'Traditional spices and masalas'),
            ('Handicrafts', 'handicrafts', 'Local handicrafts and artifacts'),
        ]

        for name, slug, desc in default_categories:
            if not Category.query.filter_by(slug=slug).first():
                category = Category(name=name, slug=slug,
                                    description=desc, is_active=True)
                db.session.add(category)
        db.session.commit()

    return app


if __name__ == '__main__':
    app = create_app(os.environ.get('FLASK_ENV', 'development'))
    app.run(host='0.0.0.0', port=5000, debug=True)
