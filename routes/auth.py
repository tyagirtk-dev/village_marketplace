from flask import Blueprint, render_template, redirect, url_for, flash, session
from flask_login import login_user, logout_user, login_required, current_user

from models.db import db
from models.user import User, Customer, Seller
from models.otp import OTPVerification
from utils.helpers import log_audit
from services.email_service import send_verification_email, send_forgot_password_email

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField
from wtforms.validators import DataRequired, Email, Length, EqualTo

auth_bp = Blueprint('auth', __name__)

# ---------------- FORMS ---------------- #


class RegistrationForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(2, 100)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    mobile = StringField('Mobile', validators=[DataRequired(), Length(10, 15)])
    password = PasswordField('Password', validators=[
                             DataRequired(), Length(6, 100)])
    confirm_password = PasswordField(
        'Confirm', validators=[EqualTo('password')])
    role = SelectField(
        'Role', choices=[('customer', 'Customer'), ('seller', 'Seller')])


class LoginForm(FlaskForm):
    identifier = StringField('Email or Mobile', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])


class OTPForm(FlaskForm):
    otp = StringField('OTP', validators=[DataRequired(), Length(6, 6)])


class ForgotPasswordForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])


class ResetPasswordForm(FlaskForm):
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
        existing = User.query.filter(
            (User.email == form.email.data) | (User.mobile == form.mobile.data)
        ).first()

        if existing:
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

        session['auth_email'] = user.email
        session['auth_purpose'] = 'registration'

        return redirect(url_for('auth.verify_otp'))

    return render_template('auth/register.html', form=form)


# ---------------- VERIFY OTP ---------------- #

@auth_bp.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp():
    form = OTPForm()

    if form.validate_on_submit():

        email = session.get('auth_email') or session.get('fp_email')
        purpose = session.get('auth_purpose') or session.get('fp_purpose')

        if not email or not purpose:
            flash("Session expired", "danger")
            return redirect(url_for('auth.login'))

        if OTPVerification.verify_otp(email, form.otp.data, purpose):

            # REGISTRATION FLOW
            if purpose == 'registration':
                user = User.query.filter_by(email=email).first()
                if user:
                    user.is_active = True
                    db.session.commit()

                session.clear()
                flash("Account verified successfully", "success")
                return redirect(url_for('auth.login'))

            # FORGOT PASSWORD FLOW
            if purpose == 'forgot_password':
                session.clear()
                session['reset_email'] = email
                session['fp_verified'] = True

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
                flash("Verify your email first", "warning")
                return redirect(url_for('auth.login'))

            login_user(user, remember=False)
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

            session.clear()
            session['fp_email'] = user.email
            session['fp_purpose'] = 'forgot_password'
            session['fp_verified'] = False

            return redirect(url_for('auth.verify_otp'))

        flash("Email not found", "danger")

    return render_template('auth/forgot_password.html', form=form)


# ---------------- RESET PASSWORD ---------------- #

@auth_bp.route('/reset-password', methods=['GET', 'POST'])
def reset_password():

    email = session.get('reset_email')
    verified = session.get('fp_verified')

    if not email or not verified:
        flash("Unauthorized access", "danger")
        return redirect(url_for('auth.forgot_password'))

    form = ResetPasswordForm()

    if form.validate_on_submit():

        user = User.query.filter_by(email=email).first()

        if user:
            user.set_password(form.password.data)
            db.session.commit()

            session.clear()

            flash("Password updated successfully", "success")
            return redirect(url_for('auth.login'))

        flash("User not found", "danger")

    return render_template('auth/reset_password.html', form=form)


# ---------------- LOGOUT ---------------- #

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    session.clear()

    response = redirect(url_for('auth.login'))
    response.delete_cookie('session')
    response.delete_cookie('remember_token')

    flash("Logged out successfully", "info")
    return response
