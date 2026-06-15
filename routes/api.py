from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from models.db import db
from models.product import Product, Category
from models.cart import Cart
from models.order import Order
import json

api_bp = Blueprint('api', __name__)


@api_bp.route('/products')
def api_products():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    products = Product.query.filter_by(
        status='approved').paginate(page=page, per_page=per_page)

    return jsonify({
        'products': [{
            'id': p.id,
            'name': p.name,
            'price': p.price,
            'image': p.primary_image,
            'stock': p.stock,
            'rating': p.rating
        } for p in products.items],
        'total': products.total,
        'page': products.page,
        'pages': products.pages
    })


@api_bp.route('/product/<int:product_id>')
def api_product(product_id):
    product = Product.query.get_or_404(product_id)
    return jsonify({
        'id': product.id,
        'name': product.name,
        'description': product.description,
        'price': product.price,
        'stock': product.stock,
        'images': product.images.split(',') if product.images else [],
        'rating': product.rating,
        'total_reviews': product.total_reviews,
        'seller': product.seller.store_name,
        'category': product.category.name
    })


@api_bp.route('/categories')
def api_categories():
    categories = Category.query.filter_by(is_active=True).all()
    return jsonify([{'id': c.id, 'name': c.name, 'slug': c.slug} for c in categories])


@api_bp.route('/cart/count')
@login_required
def api_cart_count():
    if current_user.role != 'customer':
        return jsonify({'count': 0})

    count = Cart.query.filter_by(
        customer_id=current_user.customer_profile.id).count()
    return jsonify({'count': count})


@api_bp.route('/notifications/unread-count')
@login_required
def api_notification_count():
    from models import Notification
    count = Notification.query.filter_by(
        user_id=current_user.id, is_read=False).count()
    return jsonify({'count': count})


@api_bp.route('/notifications/mark-read/<int:notification_id>', methods=['POST'])
@login_required
def api_mark_notification_read(notification_id):
    from models import Notification
    notification = Notification.query.get_or_404(notification_id)
    if notification.user_id == current_user.id:
        notification.is_read = True
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'success': False}), 403
