from datetime import datetime
from models.db import db


class Payment(db.Model):
    __tablename__ = 'payments'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey(
        'orders.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    # manual, crypto, upi, card
    payment_method = db.Column(db.String(50), default='manual')
    transaction_id = db.Column(db.String(100))
    # pending, completed, failed, refunded
    status = db.Column(db.String(20), default='pending')
    paid_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Wallet(db.Model):
    __tablename__ = 'wallets'

    id = db.Column(db.Integer, primary_key=True)
    seller_id = db.Column(db.Integer, db.ForeignKey(
        'sellers.id'), unique=True, nullable=False)
    available_balance = db.Column(db.Float, default=0.0)
    pending_balance = db.Column(db.Float, default=0.0)
    total_withdrawn = db.Column(db.Float, default=0.0)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    transactions = db.relationship(
        'Transaction', backref='wallet', lazy='dynamic')

    def add_balance(self, amount, description, reference_type, reference_id):
        self.available_balance += amount
        transaction = Transaction(
            wallet_id=self.id,
            amount=amount,
            type='credit',
            description=description,
            reference_type=reference_type,
            reference_id=reference_id
        )
        db.session.add(transaction)
        db.session.commit()

    def deduct_balance(self, amount, description, reference_type, reference_id):
        if self.available_balance >= amount:
            self.available_balance -= amount
            self.total_withdrawn += amount
            transaction = Transaction(
                wallet_id=self.id,
                amount=amount,
                type='debit',
                description=description,
                reference_type=reference_type,
                reference_id=reference_id
            )
            db.session.add(transaction)
            db.session.commit()
            return True
        return False


class Transaction(db.Model):
    __tablename__ = 'transactions'

    id = db.Column(db.Integer, primary_key=True)
    wallet_id = db.Column(db.Integer, db.ForeignKey(
        'wallets.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    type = db.Column(db.String(10), nullable=False)  # credit, debit
    description = db.Column(db.String(200))
    reference_type = db.Column(db.String(50))  # order, withdrawal, commission
    reference_id = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Withdrawal(db.Model):
    __tablename__ = 'withdrawals'

    id = db.Column(db.Integer, primary_key=True)
    seller_id = db.Column(db.Integer, db.ForeignKey(
        'sellers.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(50))  # bank, upi, crypto
    account_details = db.Column(db.Text)
    # pending, approved, rejected
    status = db.Column(db.String(20), default='pending')
    remarks = db.Column(db.Text)
    processed_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
