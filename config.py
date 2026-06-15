import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change')
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        'sqlite:////data/data/com.termux/files/home/village_marketplace/database/marketplace.db'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'True') == 'True'

    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', 'rtk0097@gmail.com')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', 'nvvpdtflwulcmxzh')
    MAIL_DEFAULT_SENDER = MAIL_USERNAME

    SITE_NAME = os.environ.get('SITE_NAME', 'Village Marketplace')
    SITE_URL = os.environ.get('SITE_URL', 'http://localhost:5000')
    COMMISSION_RATE = float(os.environ.get('COMMISSION_RATE', 10.0))

    UPLOAD_FOLDER = 'uploads/products'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

    RATELIMIT_DEFAULT = "100/day"
    RATELIMIT_STORAGE_URL = "memory://"

    OTP_LENGTH = 6
    OTP_EXPIRY_SECONDS = 300


class DevelopmentConfig(Config):
    DEBUG = True
    TESTING = False


class ProductionConfig(Config):
    DEBUG = False
    TESTING = False


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
