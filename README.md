Village Marketplace – Multi-Vendor E-Commerce Platform

"Flask" (https://img.shields.io/badge/Flask-3.0-blue)
"SQLAlchemy" (https://img.shields.io/badge/SQLAlchemy-2.0-red)
"Bootstrap" (https://img.shields.io/badge/Bootstrap-5.3-purple)
"License" (https://img.shields.io/badge/License-MIT-green)

Village Marketplace is an open-source multi-vendor e-commerce platform built with Flask and SQLAlchemy. The project is designed to help local businesses, artisans, and village sellers showcase and sell their products online through a modern and responsive marketplace.

✨ Features

- Multi-user roles (Admin, Seller, Customer)
- Product management system
- Category management
- Shopping cart and wishlist
- Order management
- Reviews and ratings
- Seller wallet and withdrawals
- Notifications system
- OTP verification
- Admin dashboard
- Responsive Bootstrap UI
- REST API support
- Audit logging
- Secure authentication

🛠 Tech Stack

Backend

- Python
- Flask
- Flask-Login
- Flask-SQLAlchemy
- Flask-Mail
- WTForms

Frontend

- HTML5
- Jinja2
- Bootstrap 5
- JavaScript
- Chart.js

Database

- SQLite
- PostgreSQL (Production Ready)

📁 Project Structure

village_marketplace/
├── app.py
├── config.py
├── models/
├── routes/
├── services/
├── utils/
├── templates/
├── static/
├── uploads/
├── logs/
├── database/
└── migrations/

🚀 Installation

Clone Repository

git clone https://github.com/tyagirtk-dev/village_marketplace.git
cd village_marketplace

Create Virtual Environment

python -m venv venv
source venv/bin/activate

Install Dependencies

pip install -r requirements.txt

Run Application

python app.py

Application will be available at:

http://localhost:5000

👤 User Roles

Admin

- Manage users
- Approve sellers
- Approve products
- Manage withdrawals
- View reports
- Monitor audit logs

Seller

- Manage products
- Process orders
- View wallet balance
- Request withdrawals
- Track sales

Customer

- Browse products
- Add to cart
- Place orders
- Leave reviews
- Manage profile

📦 Core Modules

Models

- User
- Customer
- Seller
- Product
- Category
- Order
- OrderItem
- Review
- Cart
- Wishlist
- Payment
- Wallet
- Transaction
- Withdrawal
- Notification
- AuditLog
- OTPVerification

Services

- Email Service
- Payment Service
- Analytics Service

APIs

- Products API
- Categories API
- Notifications API
- Cart API

🔐 Security

- Password hashing
- Session management
- CSRF protection
- OTP verification
- Audit logging
- SQLAlchemy ORM protection

📱 Mobile Friendly

The project is optimized for mobile devices and works smoothly on Android browsers and Termux development environments.

🗺 Roadmap

- Razorpay Integration
- UPI Payments
- Product Recommendations
- Advanced Analytics
- Seller Subscription Plans
- PWA Support
- Multi-language Support

🤝 Contributing

Contributions are welcome.

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push your branch
5. Open a Pull Request

📄 License

This project is licensed under the MIT License.

⭐ Support

If you like this project, consider giving it a star on GitHub.

👨‍💻 Author

Ritik Singh

GitHub: https://github.com/tyagirtk-dev

---

Made with ❤️ for local businesses and village communities.
