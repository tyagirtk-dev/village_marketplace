import os
import logging
from datetime import datetime
from flask import current_app, request
from werkzeug.utils import secure_filename
from models.db import db, AuditLog, Notification
from models.user import User


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower(
           ) in current_app.config['ALLOWED_EXTENSIONS']

       )
            db.session.add(audit)
            db.session.commit()
            except Exception as e:
        current_app.logger.error(f"Audit log failed: {e}")


            def create_notification(user_id, title, message, notification_type, link=None):
    try:
        notification = Notification(
            user_id = user_id,
            title = title,
            message = message,
            type = notification_type,
            link = link
        )
            db.session.add(notification)
            db.session.commit()
        except Exception as e:
        current_app.logger.error(f"Notification creation failed: {e}")


        def generate_order_number():
        from datetime import datetime
        import random
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        random_digits = ''.join(str(random.randint(0, 9)) for _ in range(4))
        return f'ORD-{timestamp}-{random_digits}'


        def setup_logging():
        log_dir = 'logs'
        os.makedirs(log_dir, exist_ok=True)

        logging.basicConfig(
        level = logging.INFO,
        format = '%(asctime)s %(levelname)s %(name)s %(message)s',
        handlers =[
            logging.FileHandler(os.path.join(log_dir, 'app.log')),
            logging.StreamHandler()
        ]
    )
        return logging.getLogger(__name__)
