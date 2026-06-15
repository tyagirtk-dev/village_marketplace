"""
Admin Blueprint for Village Marketplace
Complete admin panel backend with full CRUD operations, analytics, and moderation features
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, abort
from flask_login import login_required, current_user
from sqlalchemy import func, and_, or_
from datetime import datetime, timedelta
from models.db import db
from models.user import User, Seller, Customer
from models.product import Product, Category
from models.order import Order, OrderItem
from models.payment import Payment, Wallet, Transaction, Withdrawal
from models.review import Review
from models.notification import Notification
from models.audit import AuditLog
from utils.decorators import admin_required
from utils.helpers import log_audit, create_notification
from services.email_service import send_seller_approval_email, send_withdrawal_status_email
from services.payment_service import process_withdrawal, credit_seller_for_order

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


# ============================================
# DASHBOARD
# ============================================

@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    """Admin dashboard with comprehensive analytics and charts"""
    try:
        # ===== USER STATISTICS =====
        total_users = User.query.count()
        active_users = User.query.filter_by(
            is_active=True, is_suspended=False).count()
        suspended_users = User.query.filter_by(is_suspended=True).count()

        # ===== SELLER STATISTICS =====
        total_sellers = Seller.query.count()
        pending_sellers = Seller.query.filter_by(is_approved=False).count()
        approved_sellers = Seller.query.filter_by(is_approved=True).count()

        # ===== PRODUCT STATISTICS =====
        total_products = Product.query.count()
        pending_products = Product.query.filter_by(status='pending').count()
        approved_products = Product.query.filter_by(status='approved').count()

        # ===== ORDER STATISTICS =====
        total_orders = Order.query.count()
        pending_orders = Order.query.filter_by(status='pending').count()
        delivered_orders = Order.query.filter_by(status='delivered').count()

        # ===== REVENUE STATISTICS =====
        # Total revenue from completed orders
        total_revenue = db.session.query(func.sum(Order.total_amount))\
            .filter(Order.status == 'delivered').scalar() or 0

        # Total commission earned
        total_commission = db.session.query(func.sum(Order.commission_amount))\
            .filter(Order.status == 'delivered').scalar() or 0

        # ===== RECENT DATA =====
        recent_orders = Order.query.order_by(
            Order.created_at.desc()).limit(10).all()
        recent_sellers = Seller.query.order_by(
            Seller.created_at.desc()).limit(10).all()

        # ===== CHART DATA (Last 7 Days) =====
        last_7_days = []
        orders_data = []
        revenue_data = []

        for i in range(6, -1, -1):
            date = datetime.utcnow().date() - timedelta(days=i)
            last_7_days.append(date.strftime('%b %d'))

            # Orders count for this day
            day_orders = Order.query.filter(
                func.date(Order.created_at) == date
            ).count()
            orders_data.append(day_orders)

            # Revenue for this day
            day_revenue = db.session.query(func.sum(Order.total_amount))\
                .filter(func.date(Order.created_at) == date, Order.status == 'delivered')\
                .scalar() or 0
            revenue_data.append(float(day_revenue))

        return render_template('admin/dashboard.html',
                               # User stats
                               total_users=total_users,
                               active_users=active_users,
                               suspended_users=suspended_users,
                               # Seller stats
                               total_sellers=total_sellers,
                               pending_sellers=pending_sellers,
                               approved_sellers=approved_sellers,
                               # Product stats
                               total_products=total_products,
                               pending_products=pending_products,
                               approved_products=approved_products,
                               # Order stats
                               total_orders=total_orders,
                               pending_orders=pending_orders,
                               delivered_orders=delivered_orders,
                               # Revenue stats
                               total_revenue=total_revenue,
                               total_commission=total_commission,
                               # Recent data
                               recent_orders=recent_orders,
                               recent_sellers=recent_sellers,
                               # Chart data
                               labels=last_7_days,
                               orders_data=orders_data,
                               revenue_data=revenue_data)

    except Exception as e:
        flash(f'Error loading dashboard: {str(e)}', 'danger')
        return render_template('admin/dashboard.html')


# ============================================
# USER MANAGEMENT
# ============================================

@admin_bp.route('/users')
@login_required
@admin_required
def users():
    """List all users with search and pagination"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    per_page = 20

    query = User.query

    if search:
        query = query.filter(
            or_(
                User.name.ilike(f'%{search}%'),
                User.email.ilike(f'%{search}%'),
                User.mobile.ilike(f'%{search}%')
            )
        )

    users = query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=per_page)
    return render_template('admin/users.html', users=users, search=search)


@admin_bp.route('/user/<int:user_id>')
@login_required
@admin_required
def user_detail(user_id):
    """View detailed user information"""
    user = User.query.get_or_404(user_id)
    return render_template('admin/user_detail.html', user=user)


@admin_bp.route('/user/<int:user_id>/suspend', methods=['POST'])
@login_required
@admin_required
def suspend_user(user_id):
    """Suspend a user account"""
    try:
        user = User.query.get_or_404(user_id)

        if user.id == current_user.id:
            return jsonify({'success': False, 'message': 'Cannot suspend yourself'}) if request.headers.get('X-Requested-With') == 'XMLHttpRequest' else (flash('Cannot suspend yourself', 'danger'), redirect(url_for('admin.users')))

        if user.role == 'admin':
            return jsonify({'success': False, 'message': 'Cannot suspend admin users'}) if request.headers.get('X-Requested-With') == 'XMLHttpRequest' else (flash('Cannot suspend admin users', 'danger'), redirect(url_for('admin.users')))

        user.is_suspended = True
        db.session.commit()

        log_audit(current_user.id, 'user_suspended', 'user',
                  user_id, f'Suspended user: {user.email}')
        create_notification(user.id, 'Account Suspended',
                            'Your account has been suspended. Contact admin for details.', 'system')

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': f'User {user.name} suspended successfully'})

        flash(f'User {user.name} suspended successfully', 'success')
        return redirect(url_for('admin.users'))

    except Exception as e:
        db.session.rollback()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': str(e)})
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('admin.users'))


@admin_bp.route('/user/<int:user_id>/activate', methods=['POST'])
@login_required
@admin_required
def activate_user(user_id):
    """Activate a suspended user account"""
    try:
        user = User.query.get_or_404(user_id)
        user.is_suspended = False
        user.is_active = True
        db.session.commit()

        log_audit(current_user.id, 'user_activated', 'user',
                  user_id, f'Activated user: {user.email}')
        create_notification(user.id, 'Account Activated',
                            'Your account has been reactivated. You can now login.', 'system')

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': f'User {user.name} activated successfully'})

        flash(f'User {user.name} activated successfully', 'success')
        return redirect(url_for('admin.users'))

    except Exception as e:
        db.session.rollback()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': str(e)})
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('admin.users'))


@admin_bp.route('/user/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    """Permanently delete a user account"""
    try:
        user = User.query.get_or_404(user_id)

        if user.id == current_user.id:
            return jsonify({'success': False, 'message': 'Cannot delete yourself'}) if request.headers.get('X-Requested-With') == 'XMLHttpRequest' else (flash('Cannot delete yourself', 'danger'), redirect(url_for('admin.users')))

        email = user.email
        db.session.delete(user)
        db.session.commit()

        log_audit(current_user.id, 'user_deleted', 'user',
                  user_id, f'Deleted user: {email}')

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': f'User deleted successfully'})

        flash('User deleted successfully', 'success')
        return redirect(url_for('admin.users'))

    except Exception as e:
        db.session.rollback()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': str(e)})
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('admin.users'))


# ============================================
# SELLER MANAGEMENT
# ============================================

@admin_bp.route('/sellers')
@login_required
@admin_required
def sellers():
    """List all sellers with filters"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    status = request.args.get('status', 'all')
    per_page = 20

    query = Seller.query.join(User)

    if search:
        query = query.filter(
            or_(
                Seller.store_name.ilike(f'%{search}%'),
                User.name.ilike(f'%{search}%'),
                User.email.ilike(f'%{search}%')
            )
        )

    if status == 'pending':
        query = query.filter_by(is_approved=False)
    elif status == 'approved':
        query = query.filter_by(is_approved=True)
    elif status == 'suspended':
        query = query.filter(User.is_suspended == True)

    sellers = query.order_by(Seller.created_at.desc()).paginate(
        page=page, per_page=per_page)
    return render_template('admin/sellers.html', sellers=sellers, search=search, status=status)


@admin_bp.route('/seller/<int:seller_id>')
@login_required
@admin_required
def seller_detail(seller_id):
    """View detailed seller information with analytics"""
    seller = Seller.query.get_or_404(seller_id)

    # Get seller statistics
    product_count = Product.query.filter_by(seller_id=seller.id).count()
    order_count = Order.query.filter_by(seller_id=seller.id).count()
    withdrawal_count = Withdrawal.query.filter_by(seller_id=seller.id).count()
    total_sales = db.session.query(func.sum(Order.seller_earnings))\
        .filter(Order.seller_id == seller.id, Order.status == 'delivered').scalar() or 0

    return render_template('admin/seller_detail.html',
                           seller=seller,
                           product_count=product_count,
                           order_count=order_count,
                           withdrawal_count=withdrawal_count,
                           total_sales=total_sales)


@admin_bp.route('/seller/<int:seller_id>/approve', methods=['POST'])
@login_required
@admin_required
def approve_seller(seller_id):
    """Approve a seller account and create wallet"""
    try:
        seller = Seller.query.get_or_404(seller_id)

        if seller.is_approved:
            return jsonify({'success': False, 'message': 'Seller already approved'}) if request.headers.get('X-Requested-With') == 'XMLHttpRequest' else (flash('Seller already approved', 'warning'), redirect(url_for('admin.sellers')))

        seller.is_approved = True
        db.session.commit()

        # Create wallet for seller if not exists
        if not seller.wallet:
            wallet = Wallet(seller_id=seller.id)
            db.session.add(wallet)
            db.session.commit()

        # Send email notification
        send_seller_approval_email(seller)

        # Create notification
        create_notification(
            seller.user_id,
            'Seller Account Approved',
            f'Your seller account has been approved! You can now add products.',
            'approval',
            '/seller/dashboard'
        )

        log_audit(current_user.id, 'seller_approved', 'seller',
                  seller_id, f'Approved seller: {seller.store_name}')

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': f'Seller {seller.store_name} approved successfully'})

        flash(f'Seller {seller.store_name} approved successfully', 'success')
        return redirect(url_for('admin.sellers'))

    except Exception as e:
        db.session.rollback()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': str(e)})
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('admin.sellers'))


@admin_bp.route('/seller/<int:seller_id>/suspend', methods=['POST'])
@login_required
@admin_required
def suspend_seller(seller_id):
    """Suspend a seller account"""
    try:
        seller = Seller.query.get_or_404(seller_id)
        seller.user.is_suspended = True
        db.session.commit()

        log_audit(current_user.id, 'seller_suspended', 'seller',
                  seller_id, f'Suspended seller: {seller.store_name}')
        create_notification(seller.user_id, 'Account Suspended',
                            'Your seller account has been suspended. Contact admin.', 'system')

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': f'Seller {seller.store_name} suspended'})

        flash(f'Seller {seller.store_name} suspended', 'warning')
        return redirect(url_for('admin.sellers'))

    except Exception as e:
        db.session.rollback()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': str(e)})
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('admin.sellers'))


@admin_bp.route('/seller/<int:seller_id>/activate', methods=['POST'])
@login_required
@admin_required
def activate_seller(seller_id):
    """Activate a suspended seller account"""
    try:
        seller = Seller.query.get_or_404(seller_id)
        seller.user.is_suspended = False
        db.session.commit()

        log_audit(current_user.id, 'seller_activated', 'seller',
                  seller_id, f'Activated seller: {seller.store_name}')
        create_notification(seller.user_id, 'Account Activated',
                            'Your seller account has been reactivated.', 'system')

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': f'Seller {seller.store_name} activated'})

        flash(f'Seller {seller.store_name} activated', 'success')
        return redirect(url_for('admin.sellers'))

    except Exception as e:
        db.session.rollback()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': str(e)})
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('admin.sellers'))


@admin_bp.route('/seller/<int:seller_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_seller(seller_id):
    """Permanently delete a seller account"""
    try:
        seller = Seller.query.get_or_404(seller_id)
        user = seller.user

        db.session.delete(user)
        db.session.commit()

        log_audit(current_user.id, 'seller_deleted', 'seller',
                  seller_id, f'Deleted seller: {seller.store_name}')

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': 'Seller deleted successfully'})

        flash('Seller deleted successfully', 'success')
        return redirect(url_for('admin.sellers'))

    except Exception as e:
        db.session.rollback()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': str(e)})
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('admin.sellers'))


# ============================================
# PRODUCT MANAGEMENT
# ============================================

@admin_bp.route('/products')
@login_required
@admin_required
def admin_products():
    """List all products with filters"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    status = request.args.get('status', 'all')
    per_page = 20

    query = Product.query

    if search:
        query = query.filter(Product.name.ilike(f'%{search}%'))

    if status != 'all':
        query = query.filter_by(status=status)

    products = query.order_by(Product.created_at.desc()).paginate(
        page=page, per_page=per_page)
    return render_template('admin/products.html', products=products, search=search, status=status)


@admin_bp.route('/product/<int:product_id>')
@login_required
@admin_required
def admin_product_detail(product_id):
    """View detailed product information"""
    product = Product.query.get_or_404(product_id)
    return render_template('admin/product_detail.html', product=product)


@admin_bp.route('/product/<int:product_id>/approve', methods=['POST'])
@login_required
@admin_required
def approve_product(product_id):
    """Approve a product to make it live"""
    try:
        product = Product.query.get_or_404(product_id)

        if product.status == 'approved':
            return jsonify({'success': False, 'message': 'Product already approved'}) if request.headers.get('X-Requested-With') == 'XMLHttpRequest' else (flash('Product already approved', 'warning'), redirect(url_for('admin.admin_products')))

        product.status = 'approved'
        db.session.commit()

        log_audit(current_user.id, 'product_approved', 'product',
                  product_id, f'Approved product: {product.name}')
        create_notification(product.seller.user_id, 'Product Approved',
                            f'Your product "{product.name}" has been approved and is now live.', 'approval', '/seller/products')

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': f'Product {product.name} approved'})

        flash(f'Product {product.name} approved', 'success')
        return redirect(url_for('admin.admin_products'))

    except Exception as e:
        db.session.rollback()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': str(e)})
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('admin.admin_products'))


@admin_bp.route('/product/<int:product_id>/reject', methods=['POST'])
@login_required
@admin_required
def reject_product(product_id):
    """Reject a product"""
    try:
        product = Product.query.get_or_404(product_id)
        product.status = 'rejected'
        db.session.commit()

        log_audit(current_user.id, 'product_rejected', 'product',
                  product_id, f'Rejected product: {product.name}')
        create_notification(product.seller.user_id, 'Product Rejected',
                            f'Your product "{product.name}" was not approved. Please check guidelines.', 'approval', '/seller/products')

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': f'Product {product.name} rejected'})

        flash(f'Product {product.name} rejected', 'warning')
        return redirect(url_for('admin.admin_products'))

    except Exception as e:
        db.session.rollback()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': str(e)})
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('admin.admin_products'))


@admin_bp.route('/product/<int:product_id>/activate', methods=['POST'])
@login_required
@admin_required
def activate_product(product_id):
    """Activate a deactivated product"""
    try:
        product = Product.query.get_or_404(product_id)
        product.status = 'approved'
        db.session.commit()

        log_audit(current_user.id, 'product_activated', 'product',
                  product_id, f'Activated product: {product.name}')

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': f'Product {product.name} activated'})

        flash(f'Product {product.name} activated', 'success')
        return redirect(url_for('admin.admin_products'))

    except Exception as e:
        db.session.rollback()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': str(e)})
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('admin.admin_products'))


@admin_bp.route('/product/<int:product_id>/deactivate', methods=['POST'])
@login_required
@admin_required
def deactivate_product(product_id):
    """Deactivate a product (hide from store)"""
    try:
        product = Product.query.get_or_404(product_id)
        product.status = 'inactive'
        db.session.commit()

        log_audit(current_user.id, 'product_deactivated', 'product',
                  product_id, f'Deactivated product: {product.name}')

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': f'Product {product.name} deactivated'})

        flash(f'Product {product.name} deactivated', 'warning')
        return redirect(url_for('admin.admin_products'))

    except Exception as e:
        db.session.rollback()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': str(e)})
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('admin.admin_products'))


@admin_bp.route('/product/<int:product_id>/remove', methods=['POST'])
@login_required
@admin_required
def remove_product(product_id):
    """Permanently remove a product"""
    try:
        product = Product.query.get_or_404(product_id)
        db.session.delete(product)
        db.session.commit()

        log_audit(current_user.id, 'product_removed', 'product',
                  product_id, f'Removed product: {product.name}')

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': 'Product removed successfully'})

        flash('Product removed successfully', 'success')
        return redirect(url_for('admin.admin_products'))

    except Exception as e:
        db.session.rollback()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': str(e)})
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('admin.admin_products'))


# ============================================
# ORDER MANAGEMENT
# ============================================

@admin_bp.route('/orders')
@login_required
@admin_required
def orders():
    """List all orders with filters"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    status = request.args.get('status', 'all')
    per_page = 20

    query = Order.query

    if search:
        query = query.filter(Order.order_number.ilike(f'%{search}%'))

    if status != 'all':
        query = query.filter_by(status=status)

    orders = query.order_by(Order.created_at.desc()).paginate(
        page=page, per_page=per_page)
    return render_template('admin/orders.html', orders=orders, search=search, status=status)


@admin_bp.route('/order/<int:order_id>')
@login_required
@admin_required
def order_detail(order_id):
    """View detailed order information"""
    order = Order.query.get_or_404(order_id)
    return render_template('admin/order_detail.html', order=order)


@admin_bp.route('/order/<int:order_id>/status', methods=['POST'])
@login_required
@admin_required
def update_order_status(order_id):
    """Update order status and trigger wallet credit when delivered"""
    try:
        order = Order.query.get_or_404(order_id)
        new_status = request.form.get('status')

        if new_status not in ['pending', 'processing', 'shipped', 'delivered', 'cancelled']:
            return jsonify({'success': False, 'message': 'Invalid status'}) if request.headers.get('X-Requested-With') == 'XMLHttpRequest' else (flash('Invalid status', 'danger'), redirect(url_for('admin.order_detail', order_id=order_id)))

        old_status = order.status
        order.status = new_status

        if new_status == 'delivered' and old_status != 'delivered':
            order.delivered_at = datetime.utcnow()
            db.session.commit()

            # Credit seller wallet automatically
            credit_seller_for_order(order)

            # Notify customer
            create_notification(
                order.customer.user_id,
                'Order Delivered',
                f'Your order #{order.order_number} has been delivered.',
                'order',
                f'/customer/order/{order_id}'
            )

        db.session.commit()

        log_audit(current_user.id, 'order_status_updated', 'order',
                  order_id, f'Status changed from {old_status} to {new_status}')

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': f'Order status updated to {new_status}'})

        flash(f'Order status updated to {new_status}', 'success')
        return redirect(url_for('admin.order_detail', order_id=order_id))

    except Exception as e:
        db.session.rollback()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': str(e)})
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('admin.order_detail', order_id=order_id))


# ============================================
# CATEGORY MANAGEMENT
# ============================================

@admin_bp.route('/categories')
@login_required
@admin_required
def categories():
    """List all categories"""
    categories = Category.query.order_by(Category.name).all()
    return render_template('admin/categories.html', categories=categories)


@admin_bp.route('/category/add', methods=['POST'])
@login_required
@admin_required
def add_category():
    """Add a new category"""
    try:
        name = request.form.get('name')
        description = request.form.get('description')

        if not name:
            flash('Category name is required', 'danger')
            return redirect(url_for('admin.categories'))

        slug = name.lower().replace(' ', '-')

        # Check for duplicate
        existing = Category.query.filter_by(slug=slug).first()
        if existing:
            flash('Category with this name already exists', 'danger')
            return redirect(url_for('admin.categories'))

        category = Category(name=name, slug=slug,
                            description=description, is_active=True)
        db.session.add(category)
        db.session.commit()

        log_audit(current_user.id, 'category_added', 'category',
                  category.id, f'Added category: {name}')
        flash('Category added successfully', 'success')
        return redirect(url_for('admin.categories'))

    except Exception as e:
        db.session.rollback()
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('admin.categories'))


@admin_bp.route('/category/<int:category_id>/edit', methods=['POST'])
@login_required
@admin_required
def edit_category(category_id):
    """Edit an existing category"""
    try:
        category = Category.query.get_or_404(category_id)
        name = request.form.get('name')
        description = request.form.get('description')

        if not name:
            flash('Category name is required', 'danger')
            return redirect(url_for('admin.categories'))

        category.name = name
        category.description = description
        db.session.commit()

        log_audit(current_user.id, 'category_updated', 'category',
                  category_id, f'Updated category: {name}')
        flash('Category updated successfully', 'success')
        return redirect(url_for('admin.categories'))

    except Exception as e:
        db.session.rollback()
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('admin.categories'))


@admin_bp.route('/category/<int:category_id>/activate', methods=['POST'])
@login_required
@admin_required
def activate_category(category_id):
    """Activate a category"""
    try:
        category = Category.query.get_or_404(category_id)
        category.is_active = True
        db.session.commit()

        log_audit(current_user.id, 'category_activated', 'category',
                  category_id, f'Activated category: {category.name}')

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': 'Category activated'})

        flash('Category activated', 'success')
        return redirect(url_for('admin.categories'))

    except Exception as e:
        db.session.rollback()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': str(e)})
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('admin.categories'))


@admin_bp.route('/category/<int:category_id>/deactivate', methods=['POST'])
@login_required
@admin_required
def deactivate_category(category_id):
    """Deactivate a category"""
    try:
        category = Category.query.get_or_404(category_id)
        category.is_active = False
        db.session.commit()

        log_audit(current_user.id, 'category_deactivated', 'category',
                  category_id, f'Deactivated category: {category.name}')

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': 'Category deactivated'})

        flash('Category deactivated', 'warning')
        return redirect(url_for('admin.categories'))

    except Exception as e:
        db.session.rollback()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': str(e)})
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('admin.categories'))


@admin_bp.route('/category/<int:category_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_category(category_id):
    """Delete a category"""
    try:
        category = Category.query.get_or_404(category_id)

        # Check if category has products
        if category.products.count() > 0:
            flash('Cannot delete category with existing products', 'danger')
            return redirect(url_for('admin.categories'))

        db.session.delete(category)
        db.session.commit()

        log_audit(current_user.id, 'category_deleted', 'category',
                  category_id, f'Deleted category: {category.name}')
        flash('Category deleted successfully', 'success')
        return redirect(url_for('admin.categories'))

    except Exception as e:
        db.session.rollback()
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('admin.categories'))


# ============================================
# REVIEW MODERATION
# ============================================

@admin_bp.route('/reviews')
@login_required
@admin_required
def reviews():
    """List all reviews for moderation"""
    page = request.args.get('page', 1, type=int)
    per_page = 20

    reviews = Review.query.order_by(Review.created_at.desc()).paginate(
        page=page, per_page=per_page)
    return render_template('admin/reviews.html', reviews=reviews)


@admin_bp.route('/review/<int:review_id>/approve', methods=['POST'])
@login_required
@admin_required
def approve_review(review_id):
    """Approve a customer review"""
    try:
        review = Review.query.get_or_404(review_id)
        review.is_approved = True
        db.session.commit()

        # Update product rating
        review.product.update_rating()

        log_audit(current_user.id, 'review_approved', 'review', review_id,
                  f'Approved review for product: {review.product.name}')

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': 'Review approved'})

        flash('Review approved', 'success')
        return redirect(url_for('admin.reviews'))

    except Exception as e:
        db.session.rollback()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': str(e)})
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('admin.reviews'))


@admin_bp.route('/review/<int:review_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_review(review_id):
    """Delete a review"""
    try:
        review = Review.query.get_or_404(review_id)
        product = review.product

        db.session.delete(review)
        db.session.commit()

        # Update product rating
        product.update_rating()

        log_audit(current_user.id, 'review_deleted', 'review',
                  review_id, f'Deleted review for product: {product.name}')

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': 'Review deleted'})

        flash('Review deleted', 'success')
        return redirect(url_for('admin.reviews'))

    except Exception as e:
        db.session.rollback()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': str(e)})
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('admin.reviews'))


# ============================================
# WITHDRAWAL MANAGEMENT
# ============================================

@admin_bp.route('/withdrawals')
@login_required
@admin_required
def withdrawals():
    """List all withdrawal requests"""
    pending = Withdrawal.query.filter_by(status='pending').order_by(
        Withdrawal.created_at.desc()).all()
    processed = Withdrawal.query.filter(Withdrawal.status != 'pending').order_by(
        Withdrawal.processed_at.desc()).all()

    return render_template('admin/withdrawals.html', pending=pending, processed=processed)


@admin_bp.route('/withdrawal/<int:withdrawal_id>/process', methods=['POST'])
@login_required
@admin_required
def process_withdrawal_request(withdrawal_id):
    """Process withdrawal (approve or reject)"""
    try:
        action = request.form.get('action')
        remarks = request.form.get('remarks')

        if action not in ['approve', 'reject']:
            flash('Invalid action', 'danger')
            return redirect(url_for('admin.withdrawals'))

        if process_withdrawal(withdrawal_id, action, remarks):
            flash(f'Withdrawal {action}d successfully', 'success')
        else:
            flash('Failed to process withdrawal', 'danger')

        return redirect(url_for('admin.withdrawals'))

    except Exception as e:
        db.session.rollback()
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('admin.withdrawals'))


# ============================================
# REPORTS
# ============================================

@admin_bp.route('/reports')
@login_required
@admin_required
def reports():
    """Generate various reports"""
    # Seller sales report
    seller_sales = db.session.query(
        Seller.store_name,
        Seller.id,
        func.count(Order.id).label('order_count'),
        func.sum(Order.total_amount).label('total_sales'),
        func.sum(Order.commission_amount).label('total_commission')
    ).join(Order, Order.seller_id == Seller.id)\
     .filter(Order.status == 'delivered')\
     .group_by(Seller.id)\
     .order_by(func.sum(Order.total_amount).desc())\
     .limit(20).all()

    # Top selling products
    top_products = db.session.query(
        Product.name,
        Product.id,
        func.sum(OrderItem.quantity).label('total_sold'),
        func.sum(OrderItem.total).label('total_revenue')
    ).join(OrderItem, OrderItem.product_id == Product.id)\
     .join(Order, Order.id == OrderItem.order_id)\
     .filter(Order.status == 'delivered')\
     .group_by(Product.id)\
     .order_by(func.sum(OrderItem.quantity).desc())\
     .limit(20).all()

    # Monthly revenue report
    monthly_revenue = db.session.query(
        func.strftime('%Y-%m', Order.created_at).label('month'),
        func.count(Order.id).label('order_count'),
        func.sum(Order.total_amount).label('revenue'),
        func.sum(Order.commission_amount).label('commission')
    ).filter(Order.status == 'delivered')\
     .group_by(func.strftime('%Y-%m', Order.created_at))\
     .order_by(func.strftime('%Y-%m', Order.created_at).desc())\
     .limit(12).all()

    return render_template('admin/reports.html',
                           seller_sales=seller_sales,
                           top_products=top_products,
                           monthly_revenue=monthly_revenue)


# ============================================
# AUDIT LOGS
# ============================================

@admin_bp.route('/audit-logs')
@login_required
@admin_required
def audit_logs():
    """View system audit logs"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    per_page = 50

    query = AuditLog.query

    if search:
        query = query.filter(
            or_(
                AuditLog.action.ilike(f'%{search}%'),
                AuditLog.target_type.ilike(f'%{search}%'),
                AuditLog.details.ilike(f'%{search}%')
            )
        )

    logs = query.order_by(AuditLog.created_at.desc()).paginate(
        page=page, per_page=per_page)
    return render_template('admin/audit_logs.html', logs=logs, search=search)


# ============================================
# SETTINGS
# ============================================

class SiteSetting(db.Model):
    """Site settings model for admin configuration"""
    __tablename__ = 'site_settings'

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text)
    description = db.Column(db.String(255))
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


@admin_bp.route('/settings', methods=['GET', 'POST'])
@login_required
@admin_required
def settings():
    """Manage site settings"""
    if request.method == 'POST':
        try:
            commission_rate = request.form.get('commission_rate', type=float)
            maintenance_mode = request.form.get('maintenance_mode') == 'on'
            seller_auto_approve = request.form.get(
                'seller_auto_approve') == 'on'

            # Update or create settings
            for key, value in [
                ('commission_rate', commission_rate),
                ('maintenance_mode', maintenance_mode),
                ('seller_auto_approve', seller_auto_approve)
            ]:
                setting = SiteSetting.query.filter_by(key=key).first()
                if setting:
                    setting.value = str(value)
                else:
                    setting = SiteSetting(key=key, value=str(value))
                    db.session.add(setting)

            db.session.commit()
            log_audit(current_user.id, 'settings_updated',
                      'system', None, 'Updated site settings')
            flash('Settings updated successfully', 'success')
            return redirect(url_for('admin.settings'))

        except Exception as e:
            db.session.rollback()
            flash(f'Error: {str(e)}', 'danger')

    # Get current settings
    commission_rate = SiteSetting.query.filter_by(
        key='commission_rate').first()
    maintenance_mode = SiteSetting.query.filter_by(
        key='maintenance_mode').first()
    seller_auto_approve = SiteSetting.query.filter_by(
        key='seller_auto_approve').first()

    return render_template('admin/settings.html',
                           commission_rate=float(
                               commission_rate.value) if commission_rate else 10.0,
                           maintenance_mode=maintenance_mode.value == 'True' if maintenance_mode else False,
                           seller_auto_approve=seller_auto_approve.value == 'True' if seller_auto_approve else False)
