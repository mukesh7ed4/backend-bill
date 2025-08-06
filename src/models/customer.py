from datetime import datetime
from src.database import db

class Customer(db.Model):
    __tablename__ = 'customers'
    id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, db.ForeignKey('shops.id'), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(50))
    email = db.Column(db.String(255))
    address = db.Column(db.Text)
    city = db.Column(db.String(100))
    state = db.Column(db.String(100))
    pincode = db.Column(db.String(20))
    gst_number = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    shop = db.relationship('Shop', backref=db.backref('customers', lazy=True))

    @classmethod
    def create(cls, shop_id, customer_data):
        customer = cls(
            shop_id=shop_id,
            name=customer_data['name'],
            phone=customer_data.get('phone'),
            email=customer_data.get('email'),
            address=customer_data.get('address'),
            city=customer_data.get('city'),
            state=customer_data.get('state'),
            pincode=customer_data.get('pincode'),
            gst_number=customer_data.get('gst_number')
        )
        db.session.add(customer)
        db.session.commit()
        return customer

    @classmethod
    def get_by_id(cls, customer_id):
        return cls.query.get(customer_id)

    @classmethod
    def get_by_shop_id(cls, shop_id, limit=None, offset=None, search=None):
        query = cls.query.filter_by(shop_id=shop_id)
        
        if search:
            query = query.filter(
                db.or_(
                    cls.name.ilike(f'%{search}%'),
                    cls.phone.ilike(f'%{search}%'),
                    cls.email.ilike(f'%{search}%')
                )
            )
        
        query = query.order_by(cls.name.asc())
        
        if limit:
            if offset:
                query = query.offset(offset)
            query = query.limit(limit)
        
        return query.all()

    @classmethod
    def search_by_phone(cls, shop_id, phone):
        return cls.query.filter(
            cls.shop_id == shop_id,
            cls.phone.ilike(f'%{phone}%')
        ).all()

    def update(self, **kwargs):
        allowed_fields = [
            'name', 'phone', 'email', 'address', 'city', 
            'state', 'pincode', 'gst_number'
        ]
        
        for field, value in kwargs.items():
            if field in allowed_fields and hasattr(self, field):
                setattr(self, field, value)
        
        db.session.commit()
        return True

    def delete(self):
        db.session.delete(self)
        db.session.commit()
        return True

    def get_invoices(self, limit=None):
        from src.models.invoice import Invoice
        query = Invoice.query.filter_by(customer_id=self.id).order_by(db.desc('invoice_date'))
        if limit:
            query = query.limit(limit)
        return query.all()

    def get_total_purchases(self):
        from src.models.invoice import Invoice
        result = db.session.query(db.func.coalesce(db.func.sum(Invoice.total_amount), 0)).filter(
            Invoice.customer_id == self.id
        ).scalar()
        return float(result)

    def get_outstanding_balance(self):
        from src.models.invoice import Invoice
        result = db.session.query(db.func.coalesce(db.func.sum(Invoice.balance_amount), 0)).filter(
            Invoice.customer_id == self.id,
            Invoice.balance_amount > 0
        ).scalar()
        return float(result)

    def get_recent_payments(self, limit=10):
        from src.models.payment import InvoicePayment
        from src.models.invoice import Invoice
        
        payments = db.session.query(
            InvoicePayment, Invoice.invoice_number, Invoice.invoice_date
        ).join(Invoice).filter(
            Invoice.customer_id == self.id
        ).order_by(
            db.desc(InvoicePayment.payment_date),
            db.desc(InvoicePayment.created_at)
        ).limit(limit).all()
        
        result = []
        for payment, invoice_number, invoice_date in payments:
            result.append({
                'id': payment.id,
                'invoice_id': payment.invoice_id,
                'amount': float(payment.amount),
                'payment_method': payment.payment_method,
                'payment_date': payment.payment_date,
                'reference_number': payment.reference_number,
                'notes': payment.notes,
                'created_at': payment.created_at,
                'updated_at': payment.updated_at,
                'invoice_number': invoice_number,
                'invoice_date': invoice_date
            })
        
        return result

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
            'name': self.name,
            'phone': self.phone,
            'email': self.email,
            'address': self.address,
            'city': self.city,
            'state': self.state,
            'pincode': self.pincode,
            'gst_number': self.gst_number,
            'created_at': format_datetime(self.created_at),
            'updated_at': format_datetime(self.updated_at)
        }

