from datetime import datetime
from models.db import db


class Order(db.Model):
    __tablename__ = 'orders'

    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(50), unique=True, nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey(
        'customers.id'), nullable=False)
    seller_id = db.Column(db.Integer, db.ForeignKey(
        'sellers.id'), nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    commission_amount = db.Column(db.Float, default=0.0)
    seller_earnings = db.Column(db.Float, default=0.0)
    # pending, processing, shipped, delivered, cancelled
    status = db.Column(db.String(20), default='pending')
    shipping_address = db.Column(db.Text, nullable=False)
    tracking_number = db.Column(db.String(100))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    delivered_at = db.Column(db.DateTime)

    # Relationships
    items = db.relationship('OrderItem', backref='order',
                            lazy='dynamic', cascade='all, delete-orphan')
    payment = db.relationship(
        'Payment', backref='order', uselist=False, cascade='all, delete-orphan')


class OrderItem(db.Model):
    __tablename__ = 'order_items'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey(
        'orders.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey(
        'products.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)  # Price at time of purchase
    total = db.Column(db.Float, nullable=False)
