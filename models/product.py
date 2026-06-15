from datetime import datetime
from models.db import db


class Category(db.Model):
    __tablename__ = 'categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    slug = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.Text)
    image = db.Column(db.String(200))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    products = db.relationship('Product', backref='category', lazy='dynamic')


class Product(db.Model):
    __tablename__ = 'products'

    id = db.Column(db.Integer, primary_key=True)
    seller_id = db.Column(db.Integer, db.ForeignKey(
        'sellers.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey(
        'categories.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, default=0)
    images = db.Column(db.String(500))  # Comma-separated image paths
    rating = db.Column(db.Float, default=0.0)
    total_reviews = db.Column(db.Integer, default=0)
    # pending, approved, rejected, inactive
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    order_items = db.relationship(
        'OrderItem', backref='product', lazy='dynamic')
    reviews = db.relationship('Review', backref='product', lazy='dynamic')
    cart_items = db.relationship('Cart', backref='product', lazy='dynamic')
    wishlist_items = db.relationship(
        'Wishlist', backref='product', lazy='dynamic')

    @property
    def primary_image(self):
        if self.images:
            return self.images.split(',')[0]
        return 'default-product.jpg'

    def update_rating(self):
        from models.review import Review
        reviews = Review.query.filter_by(product_id=self.id).all()
        if reviews:
            avg = sum(r.rating for r in reviews) / len(reviews)
            self.rating = round(avg, 1)
            self.total_reviews = len(reviews)
        else:
            self.rating = 0
            self.total_reviews = 0
        db.session.commit()
