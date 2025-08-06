from datetime import datetime
from src.database import db

class Shop(db.Model):
    __tablename__ = 'shops'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    shop_name = db.Column(db.String(255), nullable=False)
    owner_name = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(50), nullable=False)
    address = db.Column(db.Text, nullable=False)
    city = db.Column(db.String(100), nullable=False)
    state = db.Column(db.String(100), nullable=False)
    pincode = db.Column(db.String(20), nullable=False)
    gst_number = db.Column(db.String(50))
    license_number = db.Column(db.String(100))
    is_active = db.Column(db.Boolean, default=False)
    subscription_status = db.Column(db.String(50), default='inactive')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    user = db.relationship('User', backref=db.backref('shop', uselist=False))

    @classmethod
    def create(cls, user_id, shop_data):
        shop = cls(
            user_id=user_id,
            shop_name=shop_data.get('shop_name'),
            owner_name=shop_data.get('owner_name'),
            phone=shop_data.get('phone'),
            address=shop_data.get('address'),
            city=shop_data.get('city'),
            state=shop_data.get('state'),
            pincode=shop_data.get('pincode'),
            gst_number=shop_data.get('gst_number'),
            license_number=shop_data.get('license_number'),
            is_active=False,
            subscription_status='inactive'
        )
        db.session.add(shop)
        db.session.commit()
        return shop

    @classmethod
    def get_by_id(cls, shop_id):
        return cls.query.get(shop_id)

    @classmethod
    def get_by_user_id(cls, user_id):
        return cls.query.filter_by(user_id=user_id).first()

    @classmethod
    def get_all_paginated(cls, page=1, limit=10, search=''):
        from src.models.user import User
        query = cls.query.join(User)
        
        if search:
            query = query.filter(
                db.or_(
                    cls.shop_name.ilike(f'%{search}%'),
                    cls.owner_name.ilike(f'%{search}%'),
                    User.email.ilike(f'%{search}%')
                )
            )
        
        shops = query.order_by(cls.created_at.desc()).paginate(
            page=page, per_page=limit, error_out=False
        )
        
        # Add email to each shop object
        for shop in shops.items:
            shop.email = shop.user.email
        
        return shops.items

    @classmethod
    def count_all(cls):
        return cls.query.count()

    @classmethod
    def count_active(cls):
        return cls.query.filter_by(is_active=True).count()

    def activate(self):
        self.is_active = True
        self.subscription_status = 'active'
        db.session.commit()

    def deactivate(self):
        self.is_active = False
        self.subscription_status = 'inactive'
        db.session.commit()

    def update(self, shop_data):
        for key, value in shop_data.items():
            if hasattr(self, key):
                setattr(self, key, value)
        db.session.commit()

    def get_dashboard_stats(self):
        from src.models.customer import Customer
        from src.models.product import Product
        from src.models.invoice import Invoice
        
        # Get total customers
        total_customers = Customer.query.filter_by(shop_id=self.id).count()
        
        # Get total products
        total_products = Product.query.filter_by(shop_id=self.id, is_active=True).count()
        
        # Get total invoices
        total_invoices = Invoice.query.filter_by(shop_id=self.id).count()
        
        # Get total revenue
        total_revenue = db.session.query(db.func.coalesce(db.func.sum(Invoice.total_amount), 0)).filter_by(shop_id=self.id).scalar() or 0
        
        # Get today's sales
        today = datetime.now().date()
        todays_sales = db.session.query(db.func.coalesce(db.func.sum(Invoice.total_amount), 0)).filter(
            Invoice.shop_id == self.id,
            db.func.date(Invoice.invoice_date) == today
        ).scalar() or 0
        
        # Get monthly sales
        current_month = datetime.now().replace(day=1)
        monthly_sales = db.session.query(db.func.coalesce(db.func.sum(Invoice.total_amount), 0)).filter(
            Invoice.shop_id == self.id,
            Invoice.invoice_date >= current_month
        ).scalar() or 0
        
        # Get low stock products
        low_stock_products = Product.query.filter(
            Product.shop_id == self.id,
            Product.is_active == True,
            Product.stock_quantity <= Product.min_stock_level
        ).count()
        
        return {
            'total_customers': total_customers,
            'total_products': total_products,
            'total_invoices': total_invoices,
            'total_revenue': float(total_revenue),
            'todays_sales': float(todays_sales),
            'monthly_sales': float(monthly_sales),
            'low_stock_products': low_stock_products
        }

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
            'user_id': self.user_id,
            'shop_name': self.shop_name,
            'owner_name': self.owner_name,
            'phone': self.phone,
            'address': self.address,
            'city': self.city,
            'state': self.state,
            'pincode': self.pincode,
            'gst_number': self.gst_number,
            'license_number': self.license_number,
            'is_active': self.is_active,
            'subscription_status': self.subscription_status,
            'created_at': format_datetime(self.created_at),
            'updated_at': format_datetime(self.updated_at),
            'email': getattr(self, 'email', None)  # Include email if available
        }

