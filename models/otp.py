from datetime import datetime, timedelta
from models.db import db


class OTPVerification(db.Model):
    __tablename__ = 'otp_verifications'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), nullable=False)
    otp = db.Column(db.String(10), nullable=False)
    # registration, forgot_password
    purpose = db.Column(db.String(50), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    is_used = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @classmethod
    def generate_otp(cls, email, purpose, length=6):
        import random
        import string
        otp = ''.join(random.choices(string.digits, k=length))
        expires_at = datetime.utcnow() + timedelta(seconds=300)  # 5 minutes

        # Invalidate previous OTPs
        cls.query.filter_by(email=email, purpose=purpose,
                            is_used=False).update({'is_used': True})

        otp_record = cls(
            email=email,
            otp=otp,
            purpose=purpose,
            expires_at=expires_at
        )
        db.session.add(otp_record)
        db.session.commit()
        return otp

    @classmethod
    def verify_otp(cls, email, otp, purpose):
        record = cls.query.filter_by(
            email=email,
            otp=otp,
            purpose=purpose,
            is_used=False
        ).first()

        if record and record.expires_at > datetime.utcnow():
            record.is_used = True
            db.session.commit()
            return True
        return False
