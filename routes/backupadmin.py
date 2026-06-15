from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from models.db import db
from models.user import User, Seller, Customer
from models.product import Product, Category
from models.order import Order
from models.payment import Withdrawal, Transaction, Wallet
from models.audit import AuditLog
from utils.decorators import admin_required
from utils.helpers import log_audit, create_notification
from services.email_service import send_seller_approval_email, send_withdrawal_status_email
from services.payment_service import process_withdrawal
from datetime import datetime, timedelta
from sqlalchemy import func

admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    # Stats
    total_users = User.query.count()
    total_sellers = Seller.query.count()
    total_customers = Customer.query.count()
    total_products = Product.query.count()
    pending_products = Product.query.filter_by(status='pending').count()
    total_orders = Order.query.count()
    pending_orders = Order.query.filter_by(status='pending').count()

    # Revenue calculation
    completed_orders = Order.query.filter_by(status='delivered').all()
    total_revenue = sum(order.total_amount for order in completed_orders)
    total_commission = sum(
        order.commission_amount for order in completed_orders)

    # Recent activity
    recent_orders = Order.query.order_by(
        Order.created_at.desc()).limit(5).all()
    recent_sellers = Seller.query.order_by(
        Seller.created_at.desc()).limit(5).all()

    # Chart data for last 7 days
    last_7_days = []
    orders_data = []
    revenue_data = []

    for i in range(6, -1, -1):
        date = datetime.utcnow().date() - timedelta(days=i)
        last_7_days.append(date.strftime('%b %d'))

        day_orders = Order.query.filter(
            func.date(Order.created_at) == date).count()
        orders_data.append(day_orders)

        day_revenue = db.session.query(func.sum(Order.total_amount)).filter(
            func.date(Order.created_at) == date, Order.status == 'delivered').scalar() or 0
        revenue_data.append(float(day_revenue))

    return render_template('admin/dashboard.html',
                           total_users=total_users,
                           total_sellers=total_sellers,
                           total_customers=total_customers,
                           total_products=total_products,
                           pending_products=pending_products,
                           total_orders=total_orders,
                           pending_orders=pending_orders,
                           total_revenue=total_revenue,
                           total_commission=total_commission,
                           recent_orders=recent_orders,
                           recent_sellers=recent_sellers,
                           labels=last_7_days,
                           orders_data=orders_data,
                           revenue_data=revenue_data)

# Seller Management


@admin_bp.route('/sellers')
@admin_required
def sellers():
    sellers = Seller.query.all()
    return render_template('admin/sellers.html', sellers=sellers)


@admin_bp.route('/seller/<int:seller_id>/approve', methods=['POST'])
@admin_required
def approve_seller(seller_id):
    seller = Seller.query.get_or_404(seller_id)
    seller.is_approved = True
    db.session.commit()

    # Create wallet for seller
    if not seller.wallet:
        wallet = Wallet(seller_id=seller.id)
        db.session.add(wallet)
        db.session.commit()

    # Send email notification
    send_seller_approval_email(seller)

    create_notification(
        seller.user_id,
        'Seller Account Approved',
        'Your seller account has been approved! You can now add products.',
        'approval',
        '/seller/dashboard'
    )

    log_audit(current_user.id, 'seller_approved', 'seller',
              seller.id, f'Approved seller: {seller.store_name}')
    flash(f'Seller {seller.store_name} approved successfully.', 'success')
    return redirect(url_for('admin.sellers'))


@admin_bp.route('/seller/<int:seller_id>/suspend', methods=['POST'])
@admin_required
def suspend_seller(seller_id):
    seller = Seller.query.get_or_404(seller_id)
    seller.user.is_suspended = True
    db.session.commit()

    log_audit(current_user.id, 'seller_suspended', 'seller',
              seller.id, f'Suspended seller: {seller.store_name}')
    flash(f'Seller {seller.store_name} suspended.', 'warning')
    return redirect(url_for('admin.sellers'))


@admin_bp.route('/seller/<int:seller_id>/delete', methods=['POST'])
@admin_required
def delete_seller(seller_id):
    seller = Seller.query.get_or_404(seller_id)
    user = seller.user

    # Delete all related data (cascade will handle)
    db.session.delete(user)
    db.session.commit()

    log_audit(current_user.id, 'seller_deleted', 'seller',
              seller_id, f'Deleted seller: {seller.store_name}')
    flash('Seller deleted successfully.', 'success')
    return redirect(url_for('admin.sellers'))

# Product Management


@admin_bp.route('/products')
@admin_required
def admin_products():
    status = request.args.get('status', 'all')
    query = Product.query

    if status != 'all':
        query = query.filter_by(status=status)

    products = query.order_by(Product.created_at.desc()).all()
    return render_template('admin/products.html', products=products, status_filter=status)


@admin_bp.route('/product/<int:product_id>/approve', methods=['POST'])
@admin_required
def approve_product(product_id):
    product = Product.query.get_or_404(product_id)
    product.status = 'approved'
    db.session.commit()

    create_notification(
        product.seller.user_id,
        'Product Approved',
        f'Your product "{product.name}" has been approved and is now live.',
        'approval',
        '/seller/products'
    )

    log_audit(current_user.id, 'product_approved', 'product',
              product.id, f'Approved product: {product.name}')
    flash('Product approved.', 'success')
    return redirect(url_for('admin.admin_products'))


@admin_bp.route('/product/<int:product_id>/reject', methods=['POST'])
@admin_required
def reject_product(product_id):
    product = Product.query.get_or_404(product_id)
    product.status = 'rejected'
    db.session.commit()

    create_notification(
        product.seller.user_id,
        'Product Rejected',
        f'Your product "{product.name}" was not approved. Please check guidelines.',
        'approval',
        '/seller/products'
    )

    log_audit(current_user.id, 'product_rejected', 'product',
              product.id, f'Rejected product: {product.name}')
    flash('Product rejected.', 'warning')
    return redirect(url_for('admin.admin_products'))


@admin_bp.route('/product/<int:product_id>/remove', methods=['POST'])
@admin_required
def remove_product(product_id):
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()

    log_audit(current_user.id, 'product_removed', 'product',
              product_id, f'Removed product: {product.name}')
    flash('Product removed.', 'success')
    return redirect(url_for('admin.admin_products'))

# Withdrawal Management


@admin_bp.route('/withdrawals')
@admin_required
def withdrawals():
    pending = Withdrawal.query.filter_by(status='pending').order_by(
        Withdrawal.created_at.desc()).all()
    processed = Withdrawal.query.filter(Withdrawal.status != 'pending').order_by(
        Withdrawal.processed_at.desc()).all()
    return render_template('admin/withdrawals.html', pending=pending, processed=processed)


@admin_bp.route('/withdrawal/<int:withdrawal_id>/process', methods=['POST'])
@admin_required
def process_withdrawal_request(withdrawal_id):
    action = request.form.get('action')
    remarks = request.form.get('remarks')

    if process_withdrawal(withdrawal_id, action, remarks):
        flash(f'Withdrawal {action}d successfully.', 'success')
    else:
        flash('Failed to process withdrawal.', 'danger')

    return redirect(url_for('admin.withdrawals'))

# Categories


@admin_bp.route('/categories')
@admin_required
def categories():
    categories = Category.query.all()
    return render_template('admin/categories.html', categories=categories)


@admin_bp.route('/category/add', methods=['POST'])
@admin_required
def add_category():
    name = request.form.get('name')
    slug = name.lower().replace(' ', '-')
    description = request.form.get('description')

    category = Category(name=name, slug=slug, description=description)
    db.session.add(category)
    db.session.commit()

    log_audit(current_user.id, 'category_added', 'category',
              category.id, f'Added category: {name}')
    flash('Category added.', 'success')
    return redirect(url_for('admin.categories'))


@admin_bp.route('/category/<int:category_id>/delete', methods=['POST'])
@admin_required
def delete_category(category_id):
    category = Category.query.get_or_404(category_id)
    db.session.delete(category)
    db.session.commit()

    log_audit(current_user.id, 'category_deleted', 'category',
              category_id, f'Deleted category: {category.name}')
    flash('Category deleted.', 'success')
    return redirect(url_for('admin.categories'))

# Audit Logs


@admin_bp.route('/audit-logs')
@admin_required
def audit_logs():
    page = request.args.get('page', 1, type=int)
    per_page = 50

    logs = AuditLog.query.order_by(AuditLog.created_at.desc()).paginate(
        page=page, per_page=per_page)
    return render_template('admin/audit_logs.html', logs=logs)

# Reports


@admin_bp.route('/reports')
@admin_required
def reports():
    # Sales report by seller
    seller_sales = db.session.query(
        Seller.store_name,
        func.count(Order.id).label('order_count'),
        func.sum(Order.total_amount).label('total_sales'),
        func.sum(Order.commission_amount).label('total_commission')
    ).join(Order, Order.seller_id == Seller.id)\
     .filter(Order.status == 'delivered')\
     .group_by(Seller.id).all()

    return render_template('admin/reports.html', seller_sales=seller_sales)
