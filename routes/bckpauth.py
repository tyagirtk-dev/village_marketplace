from flask import Blueprint
from flask import render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from models.db import db
from models.user import User, Customer, Seller
from models.otp import OTPVerification
from utils.decorators import login_required as role_login_required
from utils.helpers import log_audit
from services.email_service import send_verification_email, send_forgot_password_email
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField
from wtforms.validators import DataRequired, Email, Length, EqualTo, Regexp
import bcrypt

auth_bp = Blueprint('auth', __name__)
limiter = Limiter(get_remote_address, app=None)

# Forms


class RegistrationForm(FlaskForm):
    name = StringField('Full Name', validators=[
                       DataRequired(), Length(min=2, max=100)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    mobile = StringField('Mobile Number', validators=[DataRequired(), Length(
        min=10, max=15), Regexp(r'^[0-9]+$', message='Only numbers allowed')])
    password = PasswordField('Password', validators=[
                             DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[
                                     DataRequired(), EqualTo('password')])
    role = SelectField('I want to', choices=[(
        'customer', 'Shop as Customer'), ('seller', 'Sell Products')], validators=[DataRequired()])


class LoginForm(FlaskForm):
    identifier = StringField('Email or Mobile', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])


class OTPForm(FlaskForm):
    otp = StringField('OTP', validators=[DataRequired(), Length(min=6, max=6)])


class ForgotPasswordForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])


class ResetPasswordForm(FlaskForm):
    otp = StringField('OTP', validators=[DataRequired(), Length(min=6, max=6)])
    password = PasswordField('New Password', validators=[
                             DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[
                                     DataRequired(), EqualTo('password')])


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    form = RegistrationForm()
    if form.validate_on_submit():
        # Check if user exists
        existing_user = User.query.filter(
            (User.email == form.email.data) | (User.mobile == form.mobile.data)
        ).first()

        if existing_user:
            flash('Email or mobile number already registered.', 'danger')
            return redirect(url_for('auth.register'))

        # Create user
        user = User(
            name=form.name.data,
            email=form.email.data,
            mobile=form.mobile.data,
            role=form.role.data,
            is_active=False
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()

        # Create role-specific profile
        if form.role.data == 'customer':
            customer = Customer(user_id=user.id)
            db.session.add(customer)
        elif form.role.data == 'seller':
            seller = Seller(user_id=user.id, store_name=f"{user.name}'s Store")
            db.session.add(seller)

        db.session.commit()

        # Generate and send OTP
        otp = OTPVerification.generate_otp(user.email, 'registration')
        send_verification_email(user, otp)

        session['pending_verification_email'] = user.email
        session['pending_verification_purpose'] = 'registration'

        flash('Registration successful! Please verify your email with the OTP sent.', 'success')
        return redirect(url_for('auth.verify_otp'))

    return render_template('auth/register.html', form=form)


@auth_bp.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp():
    if 'pending_verification_email' not in session:
        flash('No pending verification.', 'warning')
        return redirect(url_for('auth.login'))

    form = OTPForm()
    if form.validate_on_submit():
        email = session['pending_verification_email']
        purpose = session.get('pending_verification_purpose', 'registration')

        if OTPVerification.verify_otp(email, form.otp.data, purpose):
            user = User.query.filter_by(email=email).first()
            if user:
                user.is_active = True
                db.session.commit()
                log_audit(user.id, 'email_verified', 'user', user.id)
                flash('Email verified successfully! You can now login.', 'success')
                session.pop('pending_verification_email', None)
                session.pop('pending_verification_purpose', None)
                return redirect(url_for('auth.login'))

        flash('Invalid or expired OTP. Please try again.', 'danger')

    return render_template('auth/verify_otp.html', form=form)


@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard_redirect'))

    form = LoginForm()
    if form.validate_on_submit():
        identifier = form.identifier.data
        password = form.password.data

        user = User.query.filter(
            (User.email == identifier) | (User.mobile == identifier)
        ).first()

        if user and user.check_password(password):
            if not user.is_active:
                flash(
                    'Please verify your email first. Check your inbox for OTP.', 'warning')
                return redirect(url_for('auth.login'))

            if user.is_suspended:
                flash('Your account has been suspended. Contact support.', 'danger')
                return redirect(url_for('auth.login'))

            login_user(user, remember=True)
            log_audit(user.id, 'user_login', 'user', user.id)
            flash(f'Welcome back, {user.name}!', 'success')

            # Redirect based on role
            return redirect(url_for('main.dashboard_redirect'))
        else:
            flash('Invalid credentials.', 'danger')

    return render_template('auth/login.html', form=form)


@auth_bp.route('/logout')
@login_required
def logout():
    log_audit(current_user.id, 'user_logout', 'user', current_user.id)
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.index'))


@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            otp = OTPVerification.generate_otp(user.email, 'forgot_password')
            send_forgot_password_email(user, otp)
            session['reset_email'] = user.email
            flash('OTP sent to your email. Please verify to reset password.', 'info')
            return redirect(url_for('auth.reset_password'))
        else:
            flash('Email not found.', 'danger')

    return render_template('auth/forgot_password.html', form=form)


@auth_bp.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    if 'reset_email' not in session:
        return redirect(url_for('auth.forgot_password'))

    form = ResetPasswordForm()
    if form.validate_on_submit():
        email = session['reset_email']

        if OTPVerification.verify_otp(email, form.otp.data, 'forgot_password'):
            user = User.query.filter_by(email=email).first()
            if user:
                user.set_password(form.password.data)
                db.session.commit()
                log_audit(user.id, 'password_reset', 'user', user.id)
                session.pop('reset_email', None)
                flash('Password reset successful! Please login.', 'success')
                return redirect(url_for('auth.login'))

        flash('Invalid or expired OTP.', 'danger')

    return render_template('auth/reset_password.html', form=form)
