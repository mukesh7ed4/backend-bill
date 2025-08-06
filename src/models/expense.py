from datetime import datetime
from src.models.user import db

class Expense(db.Model):
    __tablename__ = 'expenses'
    id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, db.ForeignKey('shops.id'), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    expense_date = db.Column(db.Date, nullable=False)
    payment_method = db.Column(db.String(100), default='cash')
    reference_number = db.Column(db.String(100))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    shop = db.relationship('Shop', backref=db.backref('expenses', lazy=True))

    @classmethod
    def create(cls, shop_id, expense_data):
        expense = cls(
            shop_id=shop_id,
            title=expense_data['title'],
            description=expense_data.get('description', ''),
            amount=expense_data['amount'],
            category=expense_data['category'],
            expense_date=expense_data['expense_date'],
            payment_method=expense_data.get('payment_method', 'cash'),
            reference_number=expense_data.get('reference_number', ''),
            notes=expense_data.get('notes', '')
        )
        db.session.add(expense)
        db.session.commit()
        return expense

    @classmethod
    def get_by_id(cls, expense_id):
        return cls.query.get(expense_id)

    @classmethod
    def get_by_shop_id(cls, shop_id, limit=None, offset=None, category=None, search=None, sort='latest', date_filter=None):
        query = cls.query.filter_by(shop_id=shop_id)
        
        if category:
            query = query.filter_by(category=category)
        
        if search:
            query = query.filter(
                db.or_(
                    cls.title.ilike(f'%{search}%'),
                    cls.description.ilike(f'%{search}%')
                )
            )
        
        if date_filter:
            query = query.filter(cls.expense_date == date_filter)
        
        if sort == 'latest':
            query = query.order_by(db.desc(cls.expense_date), db.desc(cls.created_at))
        elif sort == 'oldest':
            query = query.order_by(cls.expense_date.asc(), cls.created_at.asc())
        elif sort == 'amount_high':
            query = query.order_by(db.desc(cls.amount))
        elif sort == 'amount_low':
            query = query.order_by(cls.amount.asc())
        else:
            query = query.order_by(db.desc(cls.expense_date))
        
        if limit:
            if offset:
                query = query.offset(offset)
            query = query.limit(limit)
        
        return query.all()

    def delete(self):
        db.session.delete(self)
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
            'title': self.title,
            'description': self.description,
            'amount': float(self.amount),
            'category': self.category,
            'expense_date': format_datetime(self.expense_date),
            'payment_method': self.payment_method,
            'reference_number': self.reference_number,
            'notes': self.notes,
            'created_at': format_datetime(self.created_at),
            'updated_at': format_datetime(self.updated_at)
        } 