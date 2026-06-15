from functools import wraps
from flask import flash, redirect, url_for, abort
from flask_login import current_user


def login_required(role=None):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Please login to access this page.', 'warning')
                return redirect(url_for('auth.login'))

            if role and current_user.role != role and current_user.role != 'admin':
                flash('You do not have permission to access this page.', 'danger')
                return redirect(url_for('main.index'))

            return f(*args, **kwargs)
        return decorated_function
    return decorator


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


def seller_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'seller':
            abort(403)
        if current_user.seller_profile and not current_user.seller_profile.is_approved:
            flash('Your seller account is pending approval.', 'warning')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function


def customer_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'customer':
            abort(403)
        return f(*args, **kwargs)
    return decorated_function
