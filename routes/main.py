from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import current_user
from models.db import db
from models.product import Product, Category
from models.review import Review
from models.user import Seller
from sqlalchemy import or_
import math

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    per_page = 12

    # Get featured products (approved and in stock)
    products = Product.query.filter_by(status='approved').filter(
        Product.stock > 0).order_by(Product.created_at.desc())

    pagination = products.paginate(
        page=page, per_page=per_page, error_out=False)
    categories = Category.query.filter_by(is_active=True).limit(8).all()
    featured_sellers = Seller.query.filter_by(is_approved=True).limit(6).all()

    return render_template('main/index.html',
                           products=pagination.items,
                           pagination=pagination,
                           categories=categories,
                           featured_sellers=featured_sellers)


@main_bp.route('/products')
def products():
    page = request.args.get('page', 1, type=int)
    category = request.args.get('category', '')
    search = request.args.get('search', '')
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)
    seller_id = request.args.get('seller', type=int)

    per_page = 12
    query = Product.query.filter_by(
        status='approved').filter(Product.stock > 0)

    if category:
        query = query.filter_by(category_id=category)
    if search:
        query = query.filter(or_(
            Product.name.ilike(f'%{search}%'),
            Product.description.ilike(f'%{search}%')
        ))
    if min_price:
        query = query.filter(Product.price >= min_price)
    if max_price:
        query = query.filter(Product.price <= max_price)
    if seller_id:
        query = query.filter_by(seller_id=seller_id)

    pagination = query.order_by(Product.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False)
    categories = Category.query.filter_by(is_active=True).all()

    return render_template('main/products.html',
                           products=pagination.items,
                           pagination=pagination,
                           categories=categories,
                           category_id=category,
                           search_query=search)


@main_bp.route('/product/<int:product_id>')
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    if product.status != 'approved' and (not current_user.is_authenticated or current_user.role != 'admin'):
        flash('Product not available.', 'danger')
        return redirect(url_for('main.index'))

    related_products = Product.query.filter_by(category_id=product.category_id, status='approved')\
        .filter(Product.id != product.id).limit(4).all()

    reviews = product.reviews.filter_by(is_approved=True).order_by(
        Review.created_at.desc()).limit(10).all()

    return render_template('main/product_detail.html',
                           product=product,
                           related_products=related_products,
                           reviews=reviews)


@main_bp.route('/dashboard-redirect')
def dashboard_redirect():
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login'))
    
    if current_user.role == 'admin':
        return redirect(url_for('admin.dashboard'))
    elif current_user.role == 'seller':
        return redirect(url_for('seller.dashboard'))
    else:
        return redirect(url_for('customer.dashboard'))


@main_bp.route('/search-suggestions')
def search_suggestions():
    query = request.args.get('q', '')
    if len(query) < 2:
        return jsonify([])

    products = Product.query.filter(
        Product.status == 'approved',
        Product.name.ilike(f'%{query}%')
    ).limit(5).all()

    suggestions = [{'id': p.id, 'name': p.name, 'price': p.price,
                    'image': p.primary_image} for p in products]
    return jsonify(suggestions)
