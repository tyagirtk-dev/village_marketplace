import os
from datetime import datetime
from flask import current_app

from models.db import db
from models.notification import Notification
from models.audit import AuditLog


# ----------------------------
# FILE UPLOAD CHECK
# ----------------------------
def allowed_file(filename):
    return (
        '.' in filename
        and filename.rsplit('.', 1)[1].lower()
        in current_app.config.get('ALLOWED_EXTENSIONS', [])
    )


# ----------------------------
# AUDIT LOG
# ----------------------------
def log_audit(user_id, action, details=None):
    try:
        audit = AuditLog(
            user_id=user_id,
            action=action,
            details=details
        )

        db.session.add(audit)
        db.session.commit()

    except Exception as e:
        current_app.logger.error(f"Audit log failed: {e}")


# ----------------------------
# NOTIFICATION CREATE
# ----------------------------
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


# ----------------------------
# ORDER NUMBER GENERATOR
# ----------------------------
def generate_order_number():
    import random

    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    return f"ORD{timestamp}{random.randint(100, 999)}"


# ----------------------------
# SIMPLE LOGGER
# ----------------------------
def log_info(message):
    current_app.logger.info(message)


def log_error(message):
    current_app.logger.error(message)
