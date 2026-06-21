from flask_login import UserMixin
from datetime import datetime
from models.db import db


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    mobile = db.Column(db.String(20), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False,
                     default='customer')  # admin, seller, customer
    is_active = db.Column(db.Boolean, default=False)  # email verified
    is_suspended = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    customer_profile = db.relationship(
        'Customer', backref='user', uselist=False, cascade='all, delete-orphan')
    seller_profile = db.relationship(
        'Seller', backref='user', uselist=False, cascade='all, delete-orphan')
    notifications = db.relationship(
        'Notification', backref='user', lazy='dynamic')
    audit_logs = db.relationship('AuditLog', backref='user', lazy='dynamic')

    def set_password(self, password):
        import bcrypt
        self.password_hash = bcrypt.hashpw(password.encode(
            'utf-8'), bcrypt.gensalt()).decode('utf-8')

    def check_password(self, password):
        import bcrypt
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))

    def get_id(self):
        return str(self.id)


class Customer(db.Model):
    __tablename__ = 'customers'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey(
        'users.id'), unique=True, nullable=False)
    address = db.Column(db.Text)
    city = db.Column(db.String(100))
    state = db.Column(db.String(100))
    pincode = db.Column(db.String(10))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    reviews = db.relationship('Review', backref='customer', lazy='dynamic')
    wishlist = db.relationship('Wishlist', backref='customer', lazy='dynamic')
    cart_items = db.relationship('Cart', backref='customer', lazy='dynamic')
    orders = db.relationship('Order', backref='customer', lazy='dynamic')


class Seller(db.Model):
    __tablename__ = 'sellers'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey(
        'users.id'), unique=True, nullable=False)
    store_name = db.Column(db.String(100))
    store_description = db.Column(db.Text)
    store_logo = db.Column(db.String(200))
    is_approved = db.Column(db.Boolean, default=False)
    total_sales = db.Column(db.Integer, default=0)
    total_revenue = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    products = db.relationship('Product', backref='seller', lazy='dynamic')
    wallet = db.relationship('Wallet', backref='seller',
                             uselist=False, cascade='all, delete-orphan')
    withdrawals = db.relationship(
        'Withdrawal', backref='seller', lazy='dynamic')

class DeliveryAgent(db.Model):
    __tablename__ = 'delivery_agents'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), unique=True, nullable=False)
    
    # Agar Admin banayega toh ye Null rahega, agar Seller banayega toh uski Seller ID save hogi
    created_by_seller_id = db.Column(db.Integer, db.ForeignKey('sellers.id', ondelete='SET NULL'), nullable=True)
    
    vehicle_number = db.Column(db.String(50), nullable=True)
    is_available = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    user_rel = db.relationship('User', backref=db.backref('delivery_profile', uselist=False))
    seller_rel = db.relationship('Seller', backref=db.backref('my_agents', lazy='dynamic'))
