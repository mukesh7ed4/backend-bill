from datetime import datetime
from src.database import db

class PaymentVerification(db.Model):
    __tablename__ = 'payment_verifications'
    id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, db.ForeignKey('shops.id'), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    payment_method = db.Column(db.String(100), nullable=False)
    reference_number = db.Column(db.String(100))
    payment_proof = db.Column(db.Text)
    status = db.Column(db.String(50), default='pending')
    admin_notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    shop = db.relationship('Shop', backref=db.backref('payment_verifications', lazy=True))

    @classmethod
    def create(cls, shop_id, payment_data):
        verification = cls(
            shop_id=shop_id,
            amount=payment_data.get('amount'),
            payment_method=payment_data.get('payment_method'),
            reference_number=payment_data.get('reference_number'),
            payment_proof=payment_data.get('payment_proof'),
            status='pending'
        )
        db.session.add(verification)
        db.session.commit()
        return verification

    @classmethod
    def get_by_id(cls, verification_id):
        return cls.query.get(verification_id)

    @classmethod
    def get_by_shop_id(cls, shop_id):
        return cls.query.filter_by(shop_id=shop_id).order_by(cls.created_at.desc()).all()

    @classmethod
    def get_all_paginated(cls, page=1, limit=10, status=''):
        from src.models.shop import Shop
        query = cls.query.join(Shop)
        
        if status:
            query = query.filter(cls.status == status)
        
        verifications = query.order_by(cls.created_at.desc()).paginate(
            page=page, per_page=limit, error_out=False
        )
        
        # Add shop info to each verification
        for verification in verifications.items:
            verification.shop = {'shop_name': verification.shop.shop_name}
        
        return verifications.items

    @classmethod
    def count_pending(cls):
        return cls.query.filter_by(status='pending').count()

    @classmethod
    def get_total_verified_amount(cls):
        result = db.session.query(db.func.coalesce(db.func.sum(cls.amount), 0)).filter_by(status='verified').scalar()
        return result

    def verify(self, admin_notes=''):
        self.status = 'verified'
        self.admin_notes = admin_notes
        db.session.commit()

    def reject(self, admin_notes=''):
        self.status = 'rejected'
        self.admin_notes = admin_notes
        db.session.commit()

    def to_dict(self):
        def format_datetime(dt):
            if dt is None:
                return None
            if isinstance(dt, str):
                return dt
            if hasattr(dt, 'isoformat'):
                return dt.isoformat()
            return str(dt)
        
        return {
            'id': self.id,
            'shop_id': self.shop_id,
            'amount': self.amount,
            'payment_method': self.payment_method,
            'reference_number': self.reference_number,
            'payment_proof': self.payment_proof,
            'status': self.status,
            'admin_notes': self.admin_notes,
            'created_at': format_datetime(self.created_at),
            'updated_at': format_datetime(self.updated_at),
            'shop': getattr(self, 'shop', None)  # Include shop info if available
        }

class InvoicePayment(db.Model):
    __tablename__ = 'invoice_payments'
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id'), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    payment_method = db.Column(db.String(100), nullable=False)
    payment_date = db.Column(db.Date, nullable=False)
    reference_number = db.Column(db.String(100))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    invoice = db.relationship('Invoice', backref=db.backref('payments', lazy=True))

    @classmethod
    def create(cls, invoice_id, payment_data):
        payment = cls(
            invoice_id=invoice_id,
            amount=payment_data.get('amount'),
            payment_method=payment_data.get('payment_method'),
            payment_date=payment_data.get('payment_date'),
            reference_number=payment_data.get('reference_number'),
            notes=payment_data.get('notes')
        )
        db.session.add(payment)
        db.session.commit()
        return payment

    @classmethod
    def get_by_id(cls, payment_id):
        return cls.query.get(payment_id)

    @classmethod
    def get_by_invoice_id(cls, invoice_id):
        return cls.query.filter_by(invoice_id=invoice_id).order_by(cls.payment_date.desc()).all()

    def to_dict(self):
        def format_datetime(dt):
            if dt is None:
                return None
            if isinstance(dt, str):
                return dt
            if hasattr(dt, 'isoformat'):
                return dt.isoformat()
            return str(dt)
        
        return {
            'id': self.id,
            'invoice_id': self.invoice_id,
            'amount': self.amount,
            'payment_method': self.payment_method,
            'payment_date': format_datetime(self.payment_date),
            'reference_number': self.reference_number,
            'notes': self.notes,
            'created_at': format_datetime(self.created_at),
            'updated_at': format_datetime(self.updated_at)
        }

