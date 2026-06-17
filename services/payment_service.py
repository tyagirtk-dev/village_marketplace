from flask import current_app
from models.db import db
from models.payment import Wallet, Transaction, Withdrawal
from models.order import Order, OrderItem
from models.user import Seller
from utils.helpers import create_notification


def calculate_commission(amount):
    rate = current_app.config['COMMISSION_RATE']
    commission = amount * (rate / 100)
    return round(commission, 2)


def credit_seller_for_order(order):
    """Credit seller wallet when order is delivered"""
    seller = Seller.query.get(order.seller_id)
    if not seller or not seller.wallet:
        wallet = Wallet(seller_id=seller.id)
        db.session.add(wallet)
        db.session.commit()

    commission = order.commission_amount
    seller_earnings = order.seller_earnings

    seller.wallet.add_balance(
        seller_earnings,
        f'Earnings from order #{order.order_number}',
        'order',
        order.id
    )

    create_notification(
        seller.user_id,
        'Payment Received',
        f'You earned ₹{seller_earnings} from order #{order.order_number}. Commission: ₹{commission}',
        'payment',
        f'/seller/orders/{order.id}'
    )

    return True


def process_withdrawal(withdrawal_id, action, admin_remarks=None):
    withdrawal = Withdrawal.query.get(withdrawal_id)
    if not withdrawal:
        return False

    seller = Seller.query.get(withdrawal.seller_id)

    if action == 'approve':
        if seller.wallet.deduct_balance(
            withdrawal.amount,
            f'Withdrawal request #{withdrawal.id}',
            'withdrawal',
            withdrawal.id
        ):
            withdrawal.status = 'approved'
            withdrawal.processed_at = db.func.now()
            db.session.commit()

            # Send email notification
            from services.email_service import send_withdrawal_status_email
            send_withdrawal_status_email(seller, withdrawal, 'Approved')

            create_notification(
                seller.user_id,
                'Withdrawal Approved',
                f'Your withdrawal of ₹{withdrawal.amount} has been approved.',
                'payment',
                f'/seller/withdrawals'
            )
            return True
    elif action == 'reject':
        withdrawal.status = 'rejected'
        withdrawal.remarks = admin_remarks
        db.session.commit()

        send_withdrawal_status_email(seller, withdrawal, 'Rejected')
        create_notification(
            seller.user_id,
            'Withdrawal Rejected',
            f'Your withdrawal of ₹{withdrawal.amount} was rejected. Reason: {admin_remarks}',
            'payment',
            f'/seller/withdrawals'
        )
        return True

    return False
