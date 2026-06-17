from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, abort, session
from flask_login import login_required, current_user
from models.db import db
from models.user import Customer
from models.product import Product
from models.cart import Cart, Wishlist
from models.order import Order, OrderItem
from models.payment import Payment
from models.review import Review
from services.email_service import send_order_confirmation_email, send_order_shipped_email, send_order_delivered_email
from utils.decorators import login_required as role_required
from utils.helpers import log_audit, create_notification, generate_order_number
from services.payment_service import calculate_commission
from datetime import datetime

customer_bp = Blueprint('customer', __name__)


@customer_bp.route('/dashboard')
@role_required(role='customer')
def dashboard():
    customer = current_user.customer_profile
    recent_orders = Order.query.filter_by(customer_id=customer.id).order_by(
        Order.created_at.desc()).limit(5).all()
    wishlist_count = Wishlist.query.filter_by(customer_id=customer.id).count()
    cart_count = Cart.query.filter_by(customer_id=customer.id).count()

    return render_template('customer/dashboard.html',
                           recent_orders=recent_orders,
                           wishlist_count=wishlist_count,
                           cart_count=cart_count)

# Cart Management


@customer_bp.route('/cart')
@role_required(role='customer')
def cart():
    cart_items = Cart.query.filter_by(
        customer_id=current_user.customer_profile.id).all()
    total = sum(item.product.price * item.quantity for item in cart_items)
    return render_template('customer/cart.html', cart_items=cart_items, total=total)


@customer_bp.route('/add-to-cart/<int:product_id>', methods=['POST'])
@role_required(role='customer')
def add_to_cart(product_id):
    product = Product.query.get_or_404(product_id)
    quantity = int(request.form.get('quantity', 1))

    if quantity > product.stock:
        flash('Not enough stock available.', 'danger')
        return redirect(url_for('main.product_detail', product_id=product_id))

    cart_item = Cart.query.filter_by(
        customer_id=current_user.customer_profile.id,
        product_id=product_id
    ).first()

    if cart_item:
        cart_item.quantity += quantity
    else:
        cart_item = Cart(
            customer_id=current_user.customer_profile.id,
            product_id=product_id,
            quantity=quantity
        )
        db.session.add(cart_item)

    db.session.commit()
    flash(f'{product.name} added to cart.', 'success')
    return redirect(request.referrer or url_for('customer.cart'))


@customer_bp.route('/update-cart/<int:item_id>', methods=['POST'])
@role_required(role='customer')
def update_cart(item_id):
    cart_item = Cart.query.get_or_404(item_id)
    quantity = int(request.form.get('quantity', 1))

    if quantity <= 0:
        db.session.delete(cart_item)
    else:
        cart_item.quantity = quantity

    db.session.commit()
    return redirect(url_for('customer.cart'))


@customer_bp.route('/remove-from-cart/<int:item_id>')
@role_required(role='customer')
def remove_from_cart(item_id):
    cart_item = Cart.query.get_or_404(item_id)
    db.session.delete(cart_item)
    db.session.commit()
    flash('Item removed from cart.', 'success')
    return redirect(url_for('customer.cart'))

# Wishlist


@customer_bp.route('/wishlist')
@role_required(role='customer')
def wishlist():
    wishlist_items = Wishlist.query.filter_by(
        customer_id=current_user.customer_profile.id).all()
    return render_template('customer/wishlist.html', wishlist_items=wishlist_items)


@customer_bp.route('/add-to-wishlist/<int:product_id>')
@role_required(role='customer')
def add_to_wishlist(product_id):
    existing = Wishlist.query.filter_by(
        customer_id=current_user.customer_profile.id,
        product_id=product_id
    ).first()

    if not existing:
        wishlist = Wishlist(
            customer_id=current_user.customer_profile.id,
            product_id=product_id
        )
        db.session.add(wishlist)
        db.session.commit()
        flash('Added to wishlist.', 'success')
    else:
        flash('Product already in wishlist.', 'info')

    return redirect(request.referrer)


@customer_bp.route('/remove-from-wishlist/<int:product_id>')
@role_required(role='customer')
def remove_from_wishlist(product_id):
    wishlist = Wishlist.query.filter_by(
        customer_id=current_user.customer_profile.id,
        product_id=product_id
    ).first_or_404()
    db.session.delete(wishlist)
    db.session.commit()
    flash('Removed from wishlist.', 'success')
    return redirect(url_for('customer.wishlist'))

# Checkout


@customer_bp.route('/checkout', methods=['GET', 'POST'])
@role_required(role='customer')
def checkout():
    cart_items = Cart.query.filter_by(
        customer_id=current_user.customer_profile.id).all()

    if not cart_items:
        flash('Your cart is empty.', 'warning')
        return redirect(url_for('customer.cart'))

    if request.method == 'POST':
        address = request.form.get('address')
        city = request.form.get('city')
        state = request.form.get('state')
        pincode = request.form.get('pincode')
        payment_method = request.form.get('payment_method', 'manual')

        # Group items by seller
        seller_orders = {}
        for item in cart_items:
            seller_id = item.product.seller_id
            if seller_id not in seller_orders:
                seller_orders[seller_id] = []
            seller_orders[seller_id].append(item)

        # Create orders for each seller
        for seller_id, items in seller_orders.items():
            total_amount = sum(item.product.price *
                               item.quantity for item in items)
            commission = calculate_commission(total_amount)
            seller_earnings = total_amount - commission

            order = Order(
                order_number=generate_order_number(),
                customer_id=current_user.customer_profile.id,
                seller_id=seller_id,
                total_amount=total_amount,
                commission_amount=commission,
                seller_earnings=seller_earnings,
                status='pending',
                shipping_address=f"{address}, {city}, {state} - {pincode}"
            )
            db.session.add(order)
            db.session.flush()

            # Add order items
            for item in items:
                order_item = OrderItem(
                    order_id=order.id,
                    product_id=item.product_id,
                    quantity=item.quantity,
                    price=item.product.price,
                    total=item.product.price * item.quantity
                )
                db.session.add(order_item)

                # Update stock
                item.product.stock -= item.quantity

                # Delete cart item
                db.session.delete(item)

            # Create payment record
            payment = Payment(
                order_id=order.id,
                amount=total_amount,
                payment_method=payment_method,
                status='pending',
                paid_at=datetime.utcnow() if payment_method != 'manual' else None
            )
            db.session.add(payment)

            # Send notification to seller
            create_notification(
                order.seller.user_id,
                'New Order Received',
                f'You have received a new order #{order.order_number} for ₹{total_amount}',
                'order',
                f'/seller/orders/{order.id}'
            )

            # Send email to customer
            send_order_confirmation_email(order)

        db.session.commit()

        flash('Order placed successfully! You will receive updates via email.', 'success')
        return redirect(url_for('customer.orders'))

    # GET request - show checkout form
    total = sum(item.product.price * item.quantity for item in cart_items)
    customer_profile = current_user.customer_profile

    return render_template('customer/checkout.html',
                           cart_items=cart_items,
                           total=total,
                           customer=customer_profile)

# Orders


@customer_bp.route('/orders')
@role_required(role='customer')
def orders():
    orders = Order.query.filter_by(customer_id=current_user.customer_profile.id)\
        .order_by(Order.created_at.desc()).all()
    return render_template('customer/orders.html', orders=orders)


@customer_bp.route('/order/<int:order_id>')
@role_required(role='customer')
def order_detail(order_id):
    order = Order.query.get_or_404(order_id)
    if order.customer_id != current_user.customer_profile.id:
        abort(403)
    return render_template('customer/order_detail.html', order=order)


@customer_bp.route('/order/<int:order_id>/cancel', methods=['POST'])
@role_required(role='customer')
def cancel_order(order_id):
    order = Order.query.get_or_404(order_id)
    if order.customer_id != current_user.customer_profile.id or order.status != 'pending':
        flash('Order cannot be cancelled.', 'danger')
        return redirect(url_for('customer.order_detail', order_id=order_id))

    order.status = 'cancelled'
    db.session.commit()

    # Restore stock
    for item in order.items:
        item.product.stock += item.quantity

    db.session.commit()
    flash('Order cancelled successfully.', 'success')
    return redirect(url_for('customer.orders'))

# Reviews


@customer_bp.route('/write-review/<int:product_id>', methods=['GET', 'POST'])
@role_required(role='customer')
def write_review(product_id):
    product = Product.query.get_or_404(product_id)

    # Check if customer has purchased this product
    has_purchased = OrderItem.query.join(Order).filter(
        Order.customer_id == current_user.customer_profile.id,
        OrderItem.product_id == product_id,
        Order.status == 'delivered'
    ).first()

    if not has_purchased:
        flash('You can only review products you have purchased.', 'warning')
        return redirect(url_for('main.product_detail', product_id=product_id))

    existing_review = Review.query.filter_by(
        product_id=product_id,
        customer_id=current_user.customer_profile.id
    ).first()

    if request.method == 'POST':
        rating = int(request.form.get('rating'))
        comment = request.form.get('comment')

        if existing_review:
            existing_review.rating = rating
            existing_review.comment = comment
        else:
            review = Review(
                product_id=product_id,
                customer_id=current_user.customer_profile.id,
                rating=rating,
                comment=comment
            )
            db.session.add(review)

        db.session.commit()
        product.update_rating()
        flash('Thank you for your review!', 'success')
        return redirect(url_for('main.product_detail', product_id=product_id))

    return render_template('customer/write_review.html', product=product, review=existing_review)

# Profile


@customer_bp.route('/profile', methods=['GET', 'POST'])
@role_required(role='customer')
def profile():
    customer = current_user.customer_profile

    if request.method == 'POST':
        current_user.name = request.form.get('name')
        customer.address = request.form.get('address')
        customer.city = request.form.get('city')
        customer.state = request.form.get('state')
        customer.pincode = request.form.get('pincode')

        db.session.commit()
        flash('Profile updated successfully.', 'success')
        return redirect(url_for('customer.profile'))

    return render_template('customer/profile.html', customer=customer)
