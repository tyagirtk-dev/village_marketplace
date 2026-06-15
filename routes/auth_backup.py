from flask import Blueprint, render_template, redirect, url_for, flash, request, session
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

# ---------------- FORMS ---------------- #


class RegistrationForm(FlaskForm):
    name = StringField('Full Name', validators=[
                       DataRequired(), Length(2, 100)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    mobile = StringField('Mobile', validators=[DataRequired(), Length(10, 15)])
    password = PasswordField('Password', validators=[
                             DataRequired(), Length(6, 100)])
    confirm_password = PasswordField(
        'Confirm', validators=[EqualTo('password')])
    role = SelectField(
        'Role', choices=[('customer', 'Customer'), ('seller', 'Seller')])


class LoginForm(FlaskForm):
    identifier = StringField('Email/Mobile', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])


class OTPForm(FlaskForm):
    otp = StringField('OTP', validators=[DataRequired(), Length(6, 6)])


class ForgotPasswordForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])


class ResetPasswordForm(FlaskForm):
    otp = StringField('OTP', validators=[DataRequired(), Length(6, 6)])
    password = PasswordField('New Password', validators=[
                             DataRequired(), Length(6, 100)])
    confirm_password = PasswordField(
        'Confirm', validators=[EqualTo('password')])


# ---------------- REGISTER ---------------- #

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    form = RegistrationForm()

    if form.validate_on_submit():
        user = User.query.filter(
            (User.email == form.email.data) | (User.mobile == form.mobile.data)
        ).first()

        if user:
            flash("User already exists", "danger")
            return redirect(url_for('auth.register'))

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

        if form.role.data == 'customer':
            db.session.add(Customer(user_id=user.id))
        else:
            db.session.add(
                Seller(user_id=user.id, store_name=f"{user.name}'s Store"))

        db.session.commit()

        otp = OTPVerification.generate_otp(user.email, 'registration')
        send_verification_email(user, otp)

        session['pending_email'] = user.email
        session['otp_type'] = 'registration'

        return redirect(url_for('auth.verify_otp'))

    return render_template('auth/register.html', form=form)


# ---------------- VERIFY OTP (COMMON) ---------------- #

@auth_bp.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp():

    form = OTPForm()

    if form.validate_on_submit():

        email = session.get('pending_email') or session.get('fp_email')
        purpose = session.get('otp_type') or session.get('fp_type')

        if not email:
            flash("Session expired", "danger")
            return redirect(url_for('auth.login'))

        if OTPVerification.verify_otp(email, form.otp.data, purpose):

            # REGISTRATION
            if purpose == 'registration':
                user = User.query.filter_by(email=email).first()
                user.is_active = True
                db.session.commit()

                session.clear()
                flash("Account verified!", "success")
                return redirect(url_for('auth.login'))

            # FORGOT PASSWORD
            if purpose == 'forgot_password':
                session['reset_email'] = email
                session.pop('fp_email', None)

                flash("OTP verified. Now reset password.", "success")
                return redirect(url_for('auth.reset_password'))

        flash("Invalid OTP", "danger")

    return render_template('auth/verify_otp.html', form=form)


# ---------------- LOGIN ---------------- #

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard_redirect'))

    form = LoginForm()

    if form.validate_on_submit():
        user = User.query.filter(
            (User.email == form.identifier.data) |
            (User.mobile == form.identifier.data)
        ).first()

        if user and user.check_password(form.password.data):

            if not user.is_active:
                flash("Verify email first", "warning")
                return redirect(url_for('auth.login'))

            login_user(user)
            log_audit(user.id, 'login', 'user', user.id)

            return redirect(url_for('main.dashboard_redirect'))

        flash("Invalid credentials", "danger")

    return render_template('auth/login.html', form=form)


# ---------------- FORGOT PASSWORD ---------------- #

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():

    form = ForgotPasswordForm()

    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()

        if user:
            otp = OTPVerification.generate_otp(user.email, 'forgot_password')
            send_forgot_password_email(user, otp)

            session['fp_email'] = user.email
            session['fp_type'] = 'forgot_password'

            return redirect(url_for('auth.verify_otp'))

        flash("Email not found", "danger")

    return render_template('auth/forgot_password.html', form=form)


# ---------------- RESET PASSWORD ---------------- #

@auth_bp.route('/reset-password', methods=['GET', 'POST'])
def reset_password():

    if 'reset_email' not in session:
        return redirect(url_for('auth.forgot_password'))

    form = ResetPasswordForm()

    if form.validate_on_submit():

        email = session['reset_email']

        if OTPVerification.verify_otp(email, form.otp.data, 'forgot_password'):

            user = User.query.filter_by(email=email).first()
            user.set_password(form.password.data)
            db.session.commit()

            session.clear()

            flash("Password updated", "success")
            return redirect(url_for('auth.login'))

        flash("Invalid OTP", "danger")

    return render_template('auth/reset_password.html', form=form)


# ---------------- LOGOUT ---------------- #


@auth_bp.route('/logout')
@login_required
def logout():
    try:
        if current_user.is_authenticated:
            user_id = current_user.id
            log_audit(user_id, 'logout', 'user', user_id)

        logout_user()
        session.clear()
        flash('Logged out successfully', 'info')

    except Exception as e:
        print('Logout error:', e)

    return redirect(url_for('auth.login'))
