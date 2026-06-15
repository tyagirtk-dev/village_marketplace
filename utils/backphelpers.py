import os
import logging
from datetime import datetime
from flask import current_app
from models.db import db, Notification

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']


def log_audit(user_id, action, details=None):
    try:
        audit = {
            "user_id": user_id,
            "action": action,
            "details": details,
            "timestamp": datetime.utcnow()
        }
        db.session.add(audit)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(f"Audit log failed: {e}")


def create_notification(user_id, title, message, notification_type, link=None):
    try:
        notification = Notification(
            user_id=user_id,
            title=title,
            message=message,
            type=notification_type,
            link=link
        )
        db.session.add(notification)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(f"Notification creation failed: {e}")


def generate_order_number():
    import random
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    return f"ORD{timestamp}{random.randint(100,999)}"
