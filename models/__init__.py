from models.otp import OTPVerification
from models.audit import AuditLog
from models.notification import Notification
from models.cart import Cart, Wishlist
from models.review import Review
from models.payment import Payment, Wallet, Transaction, Withdrawal
from models.order import Order, OrderItem
from models.product import Category, Product
from models.user import User, Customer, Seller
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()

# Import all models to ensure registration
