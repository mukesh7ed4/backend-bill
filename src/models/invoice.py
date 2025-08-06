from datetime import datetime, date
from src.database import db

class Invoice(db.Model):
    __tablename__ = 'invoices'
    id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, db.ForeignKey('shops.id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'))
    invoice_number = db.Column(db.String(100), nullable=False)
    invoice_date = db.Column(db.Date, nullable=False)
    due_date = db.Column(db.Date)
    subtotal = db.Column(db.Numeric(10, 2), nullable=False)
    tax_amount = db.Column(db.Numeric(10, 2), default=0)
    discount_amount = db.Column(db.Numeric(10, 2), default=0)
    total_amount = db.Column(db.Numeric(10, 2), nullable=False)
    paid_amount = db.Column(db.Numeric(10, 2), default=0)
    balance_amount = db.Column(db.Numeric(10, 2), nullable=False)
    status = db.Column(db.String(50), default='pending')
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    shop = db.relationship('Shop', backref=db.backref('invoices', lazy=True))
    customer = db.relationship('Customer', backref=db.backref('invoices', lazy=True))
    items = db.relationship('InvoiceItem', backref='invoice', lazy=True, cascade='all, delete-orphan')
    payments = db.relationship('InvoicePayment', backref='invoice', lazy=True, cascade='all, delete-orphan')

    @classmethod
    def generate_invoice_number(cls, shop_id):
        count = cls.query.filter_by(shop_id=shop_id).count()
        today = date.today()
        return f"INV-{shop_id}-{today.strftime('%Y%m%d')}-{count + 1:04d}"

    @classmethod
    def create(cls, shop_id, invoice_data, items_data):
        # Generate invoice number if not provided
        invoice_number = invoice_data.get('invoice_number') or cls.generate_invoice_number(shop_id)
        
        # Calculate totals
        subtotal = sum(float(item['quantity'] or 0) * float(item['unit_price'] or 0) for item in items_data)
        tax_amount = float(invoice_data.get('tax_amount', 0) or 0)
        discount_amount = float(invoice_data.get('discount_amount', 0) or 0)
        total_amount = subtotal + tax_amount - discount_amount
        
        # Handle immediate payment if provided
        initial_payment = float(invoice_data.get('paid_amount', 0) or 0)
        balance_amount = total_amount - initial_payment
        
        # Determine initial status
        if balance_amount <= 0:
            initial_status = 'paid'
        elif initial_payment > 0:
            initial_status = 'partial'
        else:
            initial_status = 'pending'
        
        # Handle walk-in customer
        customer_id = invoice_data.get('customer_id')
        if customer_id == 'walk-in':
            customer_id = None
        
        # Create invoice
        invoice = cls(
            shop_id=shop_id,
            customer_id=customer_id,
            invoice_number=invoice_number,
            invoice_date=invoice_data['invoice_date'],
            due_date=invoice_data.get('due_date'),
            subtotal=subtotal,
            tax_amount=tax_amount,
            discount_amount=discount_amount,
            total_amount=total_amount,
            paid_amount=initial_payment,
            balance_amount=balance_amount,
            status=initial_status,
            notes=invoice_data.get('notes')
        )
        
        db.session.add(invoice)
        db.session.flush()  # Get the invoice ID
        
        # Create invoice items
        for item in items_data:
            # Validate required fields
            if not item.get('product_id'):
                raise Exception("Product ID is required for all items")
            if not item.get('quantity') or float(item['quantity'] or 0) <= 0:
                raise Exception("Valid quantity is required for all items")
            if not item.get('unit_price') or float(item['unit_price'] or 0) <= 0:
                raise Exception("Valid unit price is required for all items")
            
            quantity = float(item['quantity'] or 0)
            unit_price = float(item['unit_price'] or 0)
            total_price = quantity * unit_price
            
            # Get product details
            from src.models.product import Product
            product = Product.query.get(item['product_id'])
            if not product:
                raise Exception(f"Product with ID {item['product_id']} not found")
            
            # Create invoice item
            invoice_item = InvoiceItem(
                invoice_id=invoice.id,
                product_id=item['product_id'],
                product_name=product.name,
                unit=product.unit,
                quantity=quantity,
                unit_price=unit_price,
                total_price=total_price
            )
            
            db.session.add(invoice_item)
            
            # Update product stock
            product.stock_quantity -= quantity
        
        db.session.commit()
        return invoice

    @classmethod
    def get_by_id(cls, invoice_id):
        return cls.query.get(invoice_id)

    @classmethod
    def get_by_shop_id(cls, shop_id, limit=None, offset=None, status=None, search=None, sort='latest', date_filter=None):
        query = cls.query.filter_by(shop_id=shop_id)
        
        if status:
            query = query.filter_by(status=status)
        
        if search:
            from src.models.customer import Customer
            query = query.join(Customer).filter(
                db.or_(
                    cls.invoice_number.ilike(f'%{search}%'),
                    Customer.name.ilike(f'%{search}%')
                )
            )
        
        # Handle specific date filter
        if date_filter:
            query = query.filter(db.func.date(cls.invoice_date) == date_filter)
        
        # Handle date filtering for week/month
        if sort == 'this_week':
            query = query.filter(cls.invoice_date >= date.today() - db.timedelta(days=7))
        elif sort == 'this_month':
            query = query.filter(cls.invoice_date >= date.today().replace(day=1))
        
        # Handle sorting
        if sort == 'latest':
            query = query.order_by(db.desc(cls.invoice_date), db.desc(cls.created_at))
        elif sort == 'oldest':
            query = query.order_by(cls.invoice_date.asc(), cls.created_at.asc())
        elif sort == 'amount_high':
            query = query.order_by(db.desc(cls.total_amount))
        elif sort == 'amount_low':
            query = query.order_by(cls.total_amount.asc())
        elif sort == 'this_week':
            query = query.order_by(db.desc(cls.invoice_date))
        elif sort == 'this_month':
            query = query.order_by(db.desc(cls.invoice_date))
        else:
            query = query.order_by(db.desc(cls.invoice_date))
        
        if limit:
            if offset:
                query = query.offset(offset)
            query = query.limit(limit)
        
        return query.all()

    @classmethod
    def get_by_customer_id(cls, customer_id, shop_id, limit=None, offset=None, status=None, search=None):
        query = cls.query.filter_by(customer_id=customer_id, shop_id=shop_id)
        
        if status:
            query = query.filter_by(status=status)
        
        if search:
            query = query.filter(cls.invoice_number.ilike(f'%{search}%'))
        
        query = query.order_by(db.desc(cls.invoice_date))
        
        if limit:
            if offset:
                query = query.offset(offset)
            query = query.limit(limit)
        
        return query.all()

    def add_payment(self, amount, payment_method, payment_date=None, reference_number=None, notes=None):
        from src.models.payment import InvoicePayment
        
        if payment_date is None:
            payment_date = date.today()
        
        # Validate payment amount
        if amount <= 0:
            raise Exception("Payment amount must be positive")
        
        if amount > self.balance_amount:
            raise Exception(f"Payment amount ({amount}) cannot exceed balance amount ({self.balance_amount})")
        
        # Create payment record
        payment = InvoicePayment(
            invoice_id=self.id,
            amount=amount,
            payment_method=payment_method,
            payment_date=payment_date,
            reference_number=reference_number,
            notes=notes
        )
        
        db.session.add(payment)
        
        # Update invoice paid amount and balance
        new_paid_amount = self.paid_amount + amount
        new_balance_amount = self.total_amount - new_paid_amount
        
        # Determine status based on balance and due date
        if new_balance_amount <= 0:
            new_status = 'paid'
        elif new_paid_amount > 0:
            new_status = 'partial'
        else:
            new_status = 'pending'
        
        # Check if overdue
        if self.due_date and payment_date > self.due_date and new_balance_amount > 0:
            new_status = 'overdue'
        
        self.paid_amount = new_paid_amount
        self.balance_amount = new_balance_amount
        self.status = new_status
        
        db.session.commit()
        return True

    def update_status(self, status):
        self.status = status
        db.session.commit()
        return True

    def check_overdue_status(self):
        if self.due_date and self.balance_amount > 0:
            today = date.today()
            if today > self.due_date and self.status != 'paid':
                self.update_status('overdue')
                return True
        return False

    def get_payment_summary(self):
        total_paid = sum(payment.amount for payment in self.payments)
        remaining_balance = self.total_amount - total_paid
        payment_count = len(self.payments)
        
        return {
            'total_amount': self.total_amount,
            'total_paid': total_paid,
            'remaining_balance': remaining_balance,
            'payment_count': payment_count,
            'is_overdue': self.check_overdue_status(),
            'days_overdue': self.get_days_overdue() if self.due_date else 0
        }

    def get_days_overdue(self):
        if self.due_date and self.balance_amount > 0:
            today = date.today()
            if today > self.due_date:
                return (today - self.due_date).days
        return 0

    def process_return(self, return_items_data):
        try:
            total_return_amount = 0
            
            # Process each return item
            for item in return_items_data:
                if item['returned_quantity'] > 0:
                    # Get original invoice item
                    invoice_item = InvoiceItem.query.get(item['invoice_item_id'])
                    if not invoice_item:
                        raise Exception(f"Invoice item {item['invoice_item_id']} not found")
                    
                    # Validate return quantity
                    if item['returned_quantity'] > invoice_item.quantity:
                        raise Exception(f"Cannot return more than original quantity ({invoice_item.quantity})")
                    
                    # Calculate return amount
                    return_amount = float(item['returned_quantity']) * float(invoice_item.unit_price)
                    total_return_amount += return_amount
                    
                    # Update invoice item quantity
                    new_quantity = invoice_item.quantity - item['returned_quantity']
                    new_total_price = new_quantity * float(invoice_item.unit_price)
                    
                    invoice_item.quantity = new_quantity
                    invoice_item.total_price = new_total_price
                    
                    # Update product stock (add back returned quantity)
                    from src.models.product import Product
                    product = Product.query.get(invoice_item.product_id)
                    if product:
                        product.stock_quantity += item['returned_quantity']
            
            # Recalculate invoice totals
            new_subtotal = sum(item.total_price for item in self.items)
            new_total_amount = new_subtotal + float(self.tax_amount or 0) - float(self.discount_amount or 0)
            
            # Calculate how much of the return amount should reduce paid_amount
            current_paid_amount = float(self.paid_amount or 0)
            new_paid_amount = current_paid_amount
            
            if current_paid_amount > new_total_amount:
                # Customer has overpaid, reduce paid amount by the return amount
                new_paid_amount = new_total_amount
            elif current_paid_amount > 0:
                # Customer has partially paid, reduce paid amount proportionally
                original_total = float(self.total_amount or 0)
                if original_total > 0:
                    paid_percentage = current_paid_amount / original_total
                    # Apply the same percentage to the new total
                    new_paid_amount = min(new_total_amount, new_total_amount * paid_percentage)
                else:
                    new_paid_amount = 0
            else:
                # Customer hasn't paid anything, no refund needed
                new_paid_amount = 0
            
            # Update invoice amounts
            self.total_amount = new_total_amount
            self.paid_amount = new_paid_amount
            self.balance_amount = new_total_amount - new_paid_amount
            
            # Determine new status
            new_balance_amount = new_total_amount - new_paid_amount
            self.status = 'paid' if new_balance_amount <= 0 else ('partial' if new_paid_amount > 0 else 'pending')
            
            # Create a refund payment record if there's a refund
            refund_amount = current_paid_amount - new_paid_amount
            if refund_amount > 0:
                from src.models.payment import InvoicePayment
                refund_payment = InvoicePayment(
                    invoice_id=self.id,
                    amount=-refund_amount,
                    payment_method='refund',
                    payment_date=datetime.now().date(),
                    reference_number=f'RETURN-{datetime.now().strftime("%Y%m%d%H%M%S")}',
                    notes=f'Refund for returned items: {total_return_amount}'
                )
                db.session.add(refund_payment)
            
            db.session.commit()
            return total_return_amount
            
        except Exception as e:
            db.session.rollback()
            raise Exception(f"Database error: {e}")

    def delete(self):
        db.session.delete(self)
        db.session.commit()
        return True

    def to_dict(self, include_items=False, include_customer=False, include_payments=False):
        def format_datetime(dt):
            if dt is None:
                return None
            if isinstance(dt, str):
                return dt
            if hasattr(dt, 'isoformat'):
                return dt.isoformat()
            return str(dt)
        
        result = {
            'id': self.id,
            'shop_id': self.shop_id,
            'customer_id': self.customer_id,
            'invoice_number': self.invoice_number,
            'invoice_date': format_datetime(self.invoice_date),
            'due_date': format_datetime(self.due_date),
            'subtotal': float(self.subtotal),
            'tax_amount': float(self.tax_amount),
            'discount_amount': float(self.discount_amount),
            'total_amount': float(self.total_amount),
            'paid_amount': float(self.paid_amount),
            'balance_amount': float(self.balance_amount),
            'status': self.status,
            'notes': self.notes,
            'created_at': format_datetime(self.created_at),
            'updated_at': format_datetime(self.updated_at),
            'payment_summary': self.get_payment_summary(),
            'days_overdue': self.get_days_overdue()
        }
        
        if include_items:
            result['items'] = [item.to_dict() for item in self.items]
        
        if include_customer:
            result['customer'] = self.customer.to_dict() if self.customer else None
            
        if include_payments:
            result['payments'] = [payment.to_dict() for payment in self.payments]
        
        return result

class InvoiceItem(db.Model):
    __tablename__ = 'invoice_items'
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    product_name = db.Column(db.String(255), nullable=False)
    unit = db.Column(db.String(50), nullable=False)
    quantity = db.Column(db.Numeric(10, 2), nullable=False)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)
    total_price = db.Column(db.Numeric(10, 2), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    product = db.relationship('Product', backref=db.backref('invoice_items', lazy=True))

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
            'product_id': self.product_id,
            'product_name': self.product_name,
            'unit': self.unit,
            'quantity': float(self.quantity),
            'unit_price': float(self.unit_price),
            'total_price': float(self.total_price),
            'created_at': format_datetime(self.created_at)
        }

