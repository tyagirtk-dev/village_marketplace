from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
from models.db import db
from models.user import Seller
from models.product import Product, Category
from models.order import Order, OrderItem
from models.payment import Wallet, Withdrawal, Transaction
from models.review import Review
from utils.decorators import login_required as role_required
from utils.helpers import save_uploaded_file, log_audit, create_notification
from services.payment_service import process_withdrawal
from services.email_service import send_order_shipped_email, send_order_delivered_email
from datetime import datetime

seller_bp = Blueprint('seller', __name__)


@seller_bp.route('/dashboard')
@role_required(role='seller')
def dashboard():
    seller = current_user.seller_profile
    if not seller.is_approved:
        flash('Your seller account is pending approval.', 'warning')
        return redirect(url_for('main.index'))

    total_products = Product.query.filter_by(seller_id=seller.id).count()
    total_orders = Order.query.filter_by(seller_id=seller.id).count()
    pending_orders = Order.query.filter_by(
    seller_id=seller.id, status='pending').count()
    total_revenue = sum(
    order.seller_earnings for order in Order.query.filter_by(
        seller_id=seller.id,
         status='delivered').all())

    recent_orders = Order.query.filter_by(
    seller_id=seller.id).order_by(
        Order.created_at.desc()).limit(5).all()
    low_stock_products = Product.query.filter(
    Product.seller_id == seller.id,
    Product.stock < 10,
     Product.status == 'approved').all()

    return render_template('seller/dashboard.html',
                         total_products=total_products,
                         total_orders=total_orders,
                         pending_orders=pending_orders,
                         total_revenue=total_revenue,
                         recent_orders=recent_orders,
                         low_stock_products=low_stock_products)

# Product Management


@seller_bp.route('/products')
@role_required(role='seller')
def products():
    seller = current_user.seller_profile
    products = Product.query.filter_by(
    seller_id=seller.id).order_by(
        Product.created_at.desc()).all()
    return render_template('seller/products.html', products=products)


@seller_bp.route('/product/add', methods=['GET', 'POST'])
@role_required(role='seller')
def add_product():
    if not current_user.seller_profile.is_approved:
        flash('Your seller account is not approved yet.', 'warning')
        return redirect(url_for('seller.dashboard'))

    categories = Category.query.filter_by(is_active=True).all()

    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        category_id = request.form.get('category_id')
        price = float(request.form.get('price'))
        stock = int(request.form.get('stock'))

        # Handle image upload
        image_file = request.files.get('image')
        image_path = None
        if image_file:
            filename = save_uploaded_file(image_file, 'products')


image_path = filename

        product = Product(
            seller_id=current_user.seller_profile.id,
            category_id=category_id,
            name=name,
            description=description,
            price=price,
            stock=stock,
            images=image_path,
            status='pending'  # Needs admin approval
        )

        db.session.add(product)
        db.session.commit()

        log_audit(
    current_user.id,
    'product_added',
    'product',
    product.id,
     f'Added product: {name}')
        flash(
    'Product added successfully! It will appear after admin approval.',
     'success')
        return redirect(url_for('seller.products'))

    return render_template('seller/add_product.html', categories=categories)

@seller_bp.route('/product/edit/<int:product_id>', methods=['GET', 'POST'])
@role_required(role='seller')
def edit_product(product_id):
    product = Product.query.get_or_404(product_id)
    if product.seller_id != current_user.seller_profile.id:
        abort(403)
    
    categories = Category.query.filter_by(is_active=True).all()
    
    if request.method == 'POST':
        product.name = request.form.get('name')
        product.description = request.form.get('description')
        product.category_id = request.form.get('category_id')
        product.price = float(request.form.get('price'))
        product.stock = int(request.form.get('stock'))
        
        image_file = request.files.get('image')
        if image_file and image_file.filename:
            image_path = save_uploaded_file(image_file, 'products')
            if image_path:
                product.images = image_path
        
        db.session.commit()
        log_audit(current_user.id, 'product_updated', 'product', product.id, f'Updated product: {product.name}')
        flash('Product updated successfully.', 'success')
        return redirect(url_for('seller.products'))
    
    return render_template('seller/edit_product.html', product=product, categories=categories)

@seller_bp.route('/product/delete/<int:product_id>', methods=['POST'])
@role_required(role='seller')
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    if product.seller_id != current_user.seller_profile.id:
        abort(403)
    
    db.session.delete(product)
    db.session.commit()
    log_audit(current_user.id, 'product_deleted', 'product', product_id, f'Deleted product: {product.name}')
    flash('Product deleted successfully.', 'success')
    return redirect(url_for('seller.products'))

# Order Management
@seller_bp.route('/orders')
@role_required(role='seller')
def orders():
    status_filter = request.args.get('status', 'all')
    query = Order.query.filter_by(seller_id=current_user.seller_profile.id)
    
    if status_filter != 'all':
        query = query.filter_by(status=status_filter)
    
    orders = query.order_by(Order.created_at.desc()).all()
    return render_template('seller/orders.html', orders=orders, status_filter=status_filter)

@seller_bp.route('/order/<int:order_id>')
@role_required(role='seller')
def order_detail(order_id):
    order = Order.query.get_or_404(order_id)
    if order.seller_id != current_user.seller_profile.id:
        abort(403)
    return render_template('seller/order_detail.html', order=order)

@seller_bp.route('/order/<int:order_id>/update-status', methods=['POST'])
@role_required(role='seller')
def update_order_status(order_id):
    order = Order.query.get_or_404(order_id)
    if order.seller_id != current_user.seller_profile.id:
        abort(403)
    
    new_status = request.form.get('status')
    tracking_number = request.form.get('tracking_number')
    
    old_status = order.status
    order.status = new_status
    if tracking_number:
        order.tracking_number = tracking_number
    
    if new_status == 'shipped':
        order.updated_at = datetime.utcnow()
        send_order_shipped_email(order)
        create_notification(
            order.customer.user_id,
            'Order Shipped',
            f'Your order #{order.order_number} has been shipped.',
            'order',
            f'/customer/order/{order.id}'
        )
    elif new_status == 'delivered':
        order.delivered_at = datetime.utcnow()
        send_order_delivered_email(order)
        
        # Credit seller wallet
        from services.payment_service import credit_seller_for_order
        credit_seller_for_order(order)
        
        create_notification(
            order.customer.user_id,
            'Order Delivered',
            f'Your order #{order.order_number} has been delivered.',
            'order',
            f'/customer/order/{order.id}'
        )
    
    db.session.commit()
    
    log_audit(current_user.id, 'order_status_updated', 'order', order.id, f'Status changed from {old_status} to {new_status}')
    flash(f'Order status updated to {new_status}.', 'success')
    return redirect(url_for('seller.order_detail', order_id=order.id))

# Wallet & Withdrawals
@seller_bp.route('/wallet')
@role_required(role='seller')
def wallet():
    seller = current_user.seller_profile
    if not seller.wallet:
        wallet = Wallet(seller_id=seller.id)
        db.session.add(wallet)
        db.session.commit()
    
    transactions = Transaction.query.filter_by(wallet_id=seller.wallet.id).order_by(Transaction.created_at.desc()).all()
    withdrawals = Withdrawal.query.filter_by(seller_id=seller.id).order_by(Withdrawal.created_at.desc()).all()
    
    return render_template('seller/wallet.html', 
                         wallet=seller.wallet, 
                         transactions=transactions,
                         withdrawals=withdrawals)

@seller_bp.route('/request-withdrawal', methods=['POST'])
@role_required(role='seller')
def request_withdrawal():
    amount = float(request.form.get('amount'))
    payment_method = request.form.get('payment_method')
    account_details = request.form.get('account_details')
    
    seller = current_user.seller_profile
    
    if amount <= 0:
        flash('Invalid withdrawal amount.', 'danger')
        return redirect(url_for('seller.wallet'))
    
    if seller.wallet.available_balance < amount:
        flash('Insufficient balance.', 'danger')
        return redirect(url_for('seller.wallet'))
    
    withdrawal = Withdrawal(
        seller_id=seller.id,
        amount=amount,
        payment_method=payment_method,
        account_details=account_details,
        status='pending'
    )
    db.session.add(withdrawal)
    db.session.commit()
    
    create_notification(
        current_user.id,
        'Withdrawal Requested',
        f'You requested a withdrawal of ₹{amount}. Awaiting admin approval.',
        'payment',
        '/seller/wallet'
    )
    
    # Notify admin
    admin_users = User.query.filter_by(role='admin').all()
    for admin in admin_users:
        create_notification(
            admin.id,
            'New Withdrawal Request',
            f'Seller {seller.store_name} requested withdrawal of ₹{amount}',
            'payment',
            '/admin/withdrawals'
        )
    
    flash('Withdrawal request submitted successfully.', 'success')
    return redirect(url_for('seller.wallet'))

# Reviews
@seller_bp.route('/reviews')
@role_required(role='seller')
def reviews():
    seller = current_user.seller_profile
    product_ids = [p.id for p in seller.products]
    reviews = Review.query.filter(Review.product_id.in_(product_ids)).order_by(Review.created_at.desc()).all()
    return render_template('seller/reviews.html', reviews=reviews)
