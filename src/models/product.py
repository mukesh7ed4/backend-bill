from datetime import datetime
from src.database import db

class Product(db.Model):
    __tablename__ = 'products'
    id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, db.ForeignKey('shops.id'), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    brand = db.Column(db.String(100))
    description = db.Column(db.Text)
    unit = db.Column(db.String(50), nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    stock_quantity = db.Column(db.Integer, default=0)
    min_stock_level = db.Column(db.Integer, default=0)
    barcode = db.Column(db.String(100))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    shop = db.relationship('Shop', backref=db.backref('products', lazy=True))

    @classmethod
    def create(cls, shop_id, product_data):
        product = cls(
            shop_id=shop_id,
            name=product_data['name'],
            category=product_data['category'],
            brand=product_data.get('brand'),
            description=product_data.get('description'),
            unit=product_data['unit'],
            price=product_data['price'],
            stock_quantity=product_data.get('stock_quantity', 0),
            min_stock_level=product_data.get('min_stock_level', 0),
            barcode=product_data.get('barcode')
        )
        db.session.add(product)
        db.session.commit()
        return product

    @classmethod
    def get_by_id(cls, product_id):
        return cls.query.get(product_id)

    @classmethod
    def get_by_shop_id(cls, shop_id, limit=None, offset=None, search=None, category=None, active_only=True):
        query = cls.query.filter_by(shop_id=shop_id)
        
        if active_only:
            query = query.filter_by(is_active=True)
        
        if search:
            query = query.filter(
                db.or_(
                    cls.name.ilike(f'%{search}%'),
                    cls.brand.ilike(f'%{search}%'),
                    cls.barcode.ilike(f'%{search}%')
                )
            )
        
        if category:
            query = query.filter_by(category=category)
        
        query = query.order_by(cls.name.asc())
        
        if limit:
            if offset:
                query = query.offset(offset)
            query = query.limit(limit)
        
        return query.all()

    @classmethod
    def get_categories(cls, shop_id):
        categories = db.session.query(cls.category).filter(
            cls.shop_id == shop_id,
            cls.is_active == True
        ).distinct().order_by(cls.category).all()
        
        return [cat[0] for cat in categories if cat[0]]

    @classmethod
    def get_low_stock_products(cls, shop_id):
        return cls.query.filter(
            cls.shop_id == shop_id,
            cls.is_active == True,
            cls.stock_quantity <= cls.min_stock_level
        ).order_by(cls.stock_quantity.asc()).all()

    @classmethod
    def search_by_barcode(cls, shop_id, barcode):
        return cls.query.filter(
            cls.shop_id == shop_id,
            cls.barcode == barcode,
            cls.is_active == True
        ).first()

    def update(self, **kwargs):
        allowed_fields = [
            'name', 'category', 'brand', 'description', 'unit', 'price',
            'stock_quantity', 'min_stock_level', 'barcode', 'is_active'
        ]
        
        for field, value in kwargs.items():
            if field in allowed_fields and hasattr(self, field):
                setattr(self, field, value)
        
        db.session.commit()
        return True

    def update_stock(self, quantity_change):
        new_quantity = max(0, self.stock_quantity + quantity_change)
        return self.update(stock_quantity=new_quantity)

    def deactivate(self):
        return self.update(is_active=False)

    def activate(self):
        return self.update(is_active=True)

    def is_low_stock(self):
        return self.stock_quantity <= self.min_stock_level

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
            'category': self.category,
            'brand': self.brand,
            'description': self.description,
            'unit': self.unit,
            'price': float(self.price),
            'stock_quantity': self.stock_quantity,
            'min_stock_level': self.min_stock_level,
            'barcode': self.barcode,
            'is_active': bool(self.is_active),
            'is_low_stock': self.is_low_stock(),
            'created_at': format_datetime(self.created_at),
            'updated_at': format_datetime(self.updated_at)
        }

