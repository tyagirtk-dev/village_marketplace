from flask import render_template, current_app
from flask_mail import Message
from threading import Thread
from models.db import db


def send_async_email(app, msg):
    with app.app_context():
        from flask_mail import Mail
        mail = Mail(app)
        mail.send(msg)


def send_email(to, subject, template, **kwargs):
    app = current_app._get_current_object()
    html = render_template(f'emails/{template}.html', **kwargs)
    msg = Message(subject, recipients=[to], html=html)

    thr = Thread(target=send_async_email, args=(app, msg))
    thr.start()
    return thr

# Specific email templates


def send_verification_email(user, otp):
    send_email(
        user.email,
        f'Verify Your {current_app.config["SITE_NAME"]} Account',
        'verification',
        name=user.name,
        otp=otp,
        site_name=current_app.config['SITE_NAME']
    )


def send_forgot_password_email(user, otp):
    send_email(
        user.email,
        f'Password Reset - {current_app.config["SITE_NAME"]}',
        'forgot_password',
        name=user.name,
        otp=otp,
        site_name=current_app.config['SITE_NAME']
    )


def send_seller_approval_email(seller):
    send_email(
        seller.user.email,
        f'Seller Account Approved - {current_app.config["SITE_NAME"]}',
        'seller_approval',
        name=seller.user.name,
        store_name=seller.store_name,
        site_name=current_app.config['SITE_NAME']
    )


def send_order_confirmation_email(order):
    send_email(
        order.customer.user.email,
        f'Order Confirmation #{order.order_number}',
        'order_confirmation',
        order=order,
        site_name=current_app.config['SITE_NAME']
    )


def send_order_shipped_email(order):
    send_email(
        order.customer.user.email,
        f'Order Shipped #{order.order_number}',
        'order_shipped',
        order=order,
        site_name=current_app.config['SITE_NAME']
    )


def send_order_delivered_email(order):
    send_email(
        order.customer.user.email,
        f'Order Delivered #{order.order_number}',
        'order_delivered',
        order=order,
        site_name=current_app.config['SITE_NAME']
    )


def send_payment_released_email(seller, amount):
    send_email(
        seller.user.email,
        f'Payment Released - {current_app.config["SITE_NAME"]}',
        'payment_released',
        name=seller.user.name,
        amount=amount,
        site_name=current_app.config['SITE_NAME']
    )


def send_withdrawal_status_email(seller, withdrawal, status):
    send_email(
        seller.user.email,
        f'Withdrawal {status} - {current_app.config["SITE_NAME"]}',
        'withdrawal_status',
        name=seller.user.name,
        amount=withdrawal.amount,
        status=status,
        remarks=withdrawal.remarks,
        site_name=current_app.config['SITE_NAME']
    )
