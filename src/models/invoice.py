import sqlite3
from datetime import datetime, date
from src.database_sqlite import get_db_connection

class Invoice:
    def __init__(self, id=None, shop_id=None, customer_id=None, invoice_number=None,
                 invoice_date=None, due_date=None, subtotal=None, tax_amount=0,
                 discount_amount=0, total_amount=None, paid_amount=0, balance_amount=None,
                 status='pending', notes=None, created_at=None, updated_at=None):
        self.id = id
        self.shop_id = shop_id
        self.customer_id = customer_id
        self.invoice_number = invoice_number
        self.invoice_date = invoice_date
        self.due_date = due_date
        self.subtotal = subtotal
        self.tax_amount = tax_amount
        self.discount_amount = discount_amount
        self.total_amount = total_amount
        self.paid_amount = paid_amount
        self.balance_amount = balance_amount
        self.status = status
        self.notes = notes
        self.created_at = created_at
        self.updated_at = updated_at

    @classmethod
    def generate_invoice_number(cls, shop_id):
        """Generate unique invoice number"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT COUNT(*) FROM invoices WHERE shop_id = ?
            ''', (shop_id,))
            count = cursor.fetchone()[0]
            
            today = date.today()
            return f"INV-{shop_id}-{today.strftime('%Y%m%d')}-{count + 1:04d}"

    @classmethod
    def create(cls, shop_id, invoice_data, items_data):
        """Create a new invoice with items"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
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
            cursor.execute('''
                INSERT INTO invoices (
                    shop_id, customer_id, invoice_number, invoice_date, due_date,
                    subtotal, tax_amount, discount_amount, total_amount,
                    paid_amount, balance_amount, status, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                shop_id, customer_id,
                invoice_number, invoice_data['invoice_date'],
                invoice_data.get('due_date'), subtotal, tax_amount,
                discount_amount, total_amount, initial_payment,
                balance_amount, initial_status, invoice_data.get('notes')
            ))
            
            invoice_id = cursor.lastrowid
            
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
                
                # Get product details for product_name and unit
                cursor.execute('SELECT name, unit FROM products WHERE id = ?', (item['product_id'],))
                product_row = cursor.fetchone()
                if not product_row:
                    raise Exception(f"Product with ID {item['product_id']} not found")
                
                product_name, unit = product_row
                
                cursor.execute('''
                    INSERT INTO invoice_items (
                        invoice_id, product_id, product_name, unit, quantity, unit_price, total_price
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    invoice_id, item['product_id'], product_name, unit, quantity,
                    unit_price, total_price
                ))
                
                # Update product stock
                cursor.execute('''
                    UPDATE products 
                    SET stock_quantity = stock_quantity - ?
                    WHERE id = ?
                ''', (quantity, item['product_id']))
            
            conn.commit()
            return cls.get_by_id(invoice_id)

    @classmethod
    def get_by_id(cls, invoice_id):
        """Get invoice by ID"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM invoices WHERE id = ?', (invoice_id,))
            row = cursor.fetchone()
            
            if row:
                return cls(*row)
            return None

    @classmethod
    def get_by_shop_id(cls, shop_id, limit=None, offset=None, status=None, search=None, sort='latest', date_filter=None):
        """Get invoices by shop ID with optional filtering and sorting"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            query = '''
                SELECT i.* FROM invoices i
                LEFT JOIN customers c ON i.customer_id = c.id
                WHERE i.shop_id = ?
            '''
            params = [shop_id]
            
            if status:
                query += ' AND i.status = ?'
                params.append(status)
            
            if search:
                query += ' AND (i.invoice_number LIKE ? OR c.name LIKE ?)'
                search_term = f'%{search}%'
                params.extend([search_term, search_term])
            
            # Handle specific date filter
            if date_filter:
                query += ' AND DATE(i.invoice_date) = ?'
                params.append(date_filter)
            
            # Handle date filtering for week/month
            if sort == 'this_week':
                query += ' AND i.invoice_date >= date("now", "weekday 0", "-6 days")'
            elif sort == 'this_month':
                query += ' AND i.invoice_date >= date("now", "start of month")'
            
            # Handle sorting
            if sort == 'latest':
                query += ' ORDER BY i.invoice_date DESC, i.created_at DESC'
            elif sort == 'oldest':
                query += ' ORDER BY i.invoice_date ASC, i.created_at ASC'
            elif sort == 'amount_high':
                query += ' ORDER BY i.total_amount DESC'
            elif sort == 'amount_low':
                query += ' ORDER BY i.total_amount ASC'
            elif sort == 'this_week':
                query += ' ORDER BY i.invoice_date DESC'
            elif sort == 'this_month':
                query += ' ORDER BY i.invoice_date DESC'
            else:
                query += ' ORDER BY i.invoice_date DESC'
            
            if limit:
                query += ' LIMIT ?'
                params.append(limit)
                if offset:
                    query += ' OFFSET ?'
                    params.append(offset)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            return [cls(*row) for row in rows]

    @classmethod
    def get_by_customer_id(cls, customer_id, shop_id, limit=None, offset=None, status=None, search=None):
        """Get invoices by customer ID with optional filtering"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            query = '''
                SELECT i.* FROM invoices i
                WHERE i.customer_id = ? AND i.shop_id = ?
            '''
            params = [customer_id, shop_id]
            
            if status:
                query += ' AND i.status = ?'
                params.append(status)
            
            if search:
                query += ' AND i.invoice_number LIKE ?'
                search_term = f'%{search}%'
                params.append(search_term)
            
            query += ' ORDER BY i.invoice_date DESC'
            
            if limit:
                query += ' LIMIT ?'
                params.append(limit)
                if offset:
                    query += ' OFFSET ?'
                    params.append(offset)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            return [cls(*row) for row in rows]

    def get_items(self):
        """Get invoice items"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, invoice_id, product_id, product_name, unit, quantity, unit_price, total_price, created_at 
                FROM invoice_items WHERE invoice_id = ?
            ''', (self.id,))
            rows = cursor.fetchall()
            
            return [InvoiceItem(*row) for row in rows]

    def get_payments(self):
        """Get invoice payments"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM invoice_payments 
                WHERE invoice_id = ? 
                ORDER BY payment_date DESC
            ''', (self.id,))
            rows = cursor.fetchall()
            
            from src.models.payment import InvoicePayment
            return [InvoicePayment(*row) for row in rows]

    def add_payment(self, amount, payment_method, payment_date=None, reference_number=None, notes=None):
        """Add payment to invoice"""
        from datetime import date, datetime
        
        if payment_date is None:
            payment_date = date.today()
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Validate payment amount
            if amount <= 0:
                raise Exception("Payment amount must be positive")
            
            if amount > self.balance_amount:
                raise Exception(f"Payment amount ({amount}) cannot exceed balance amount ({self.balance_amount})")
            
            # Create payment record
            cursor.execute('''
                INSERT INTO invoice_payments (
                    invoice_id, amount, payment_method, payment_date, 
                    reference_number, notes, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                self.id, amount, payment_method, payment_date,
                reference_number, notes, datetime.now(), datetime.now()
            ))
            
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
            
            cursor.execute('''
                UPDATE invoices 
                SET paid_amount = ?, balance_amount = ?, status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (new_paid_amount, new_balance_amount, new_status, self.id))
            
            conn.commit()
            
            # Update instance attributes
            self.paid_amount = new_paid_amount
            self.balance_amount = new_balance_amount
            self.status = new_status
            
            return True

    def update_status(self, status):
        """Update invoice status"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE invoices 
                SET status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (status, self.id))
            conn.commit()
            self.status = status
            return cursor.rowcount > 0

    def check_overdue_status(self):
        """Check and update overdue status"""
        from datetime import date
        
        if self.due_date and self.balance_amount > 0:
            today = date.today()
            if today > self.due_date and self.status != 'paid':
                self.update_status('overdue')
                return True
        return False

    def get_payment_summary(self):
        """Get payment summary for the invoice"""
        payments = self.get_payments()
        total_paid = sum(payment.amount for payment in payments)
        remaining_balance = self.total_amount - total_paid
        payment_count = len(payments)
        
        return {
            'total_amount': self.total_amount,
            'total_paid': total_paid,
            'remaining_balance': remaining_balance,
            'payment_count': payment_count,
            'is_overdue': self.check_overdue_status(),
            'days_overdue': self.get_days_overdue() if self.due_date else 0
        }

    def get_days_overdue(self):
        """Get number of days overdue"""
        from datetime import date
        
        if self.due_date and self.balance_amount > 0:
            today = date.today()
            if today > self.due_date:
                return (today - self.due_date).days
        return 0

    def process_return(self, return_items_data):
        """Process return for invoice items"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            try:
                total_return_amount = 0
                
                # Process each return item
                for item in return_items_data:
                    if item['returned_quantity'] > 0:
                        # Get original invoice item
                        cursor.execute('''
                            SELECT quantity, unit_price, total_price, product_id 
                            FROM invoice_items 
                            WHERE id = ?
                        ''', (item['invoice_item_id'],))
                        
                        original_item = cursor.fetchone()
                        if not original_item:
                            raise Exception(f"Invoice item {item['invoice_item_id']} not found")
                        
                        original_quantity, unit_price, total_price, product_id = original_item
                        
                        # Validate return quantity
                        if item['returned_quantity'] > original_quantity:
                            raise Exception(f"Cannot return more than original quantity ({original_quantity})")
                        
                        # Calculate return amount
                        return_amount = float(item['returned_quantity']) * float(unit_price)
                        total_return_amount += return_amount
                        
                        # Update invoice item quantity
                        new_quantity = original_quantity - item['returned_quantity']
                        new_total_price = new_quantity * float(unit_price)
                        
                        cursor.execute('''
                            UPDATE invoice_items 
                            SET quantity = ?, total_price = ?
                            WHERE id = ?
                        ''', (new_quantity, new_total_price, item['invoice_item_id']))
                        
                        # Update product stock (add back returned quantity)
                        cursor.execute('''
                            UPDATE products 
                            SET stock_quantity = stock_quantity + ?
                            WHERE id = ?
                        ''', (item['returned_quantity'], product_id))
                
                # Recalculate invoice totals
                cursor.execute('''
                    SELECT SUM(total_price) FROM invoice_items WHERE invoice_id = ?
                ''', (self.id,))
                
                new_subtotal = cursor.fetchone()[0] or 0
                new_total_amount = new_subtotal + float(self.tax_amount or 0) - float(self.discount_amount or 0)
                
                # Calculate how much of the return amount should reduce paid_amount
                # If customer has paid more than the new total, reduce paid_amount
                current_paid_amount = float(self.paid_amount or 0)
                new_paid_amount = current_paid_amount
                
                if current_paid_amount > new_total_amount:
                    # Customer has overpaid, reduce paid amount by the return amount
                    new_paid_amount = new_total_amount
                elif current_paid_amount > 0:
                    # Customer has partially paid, reduce paid amount proportionally
                    # Calculate what percentage of the original total was paid
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
                cursor.execute('''
                    UPDATE invoices 
                    SET total_amount = ?, paid_amount = ?, balance_amount = ?
                    WHERE id = ?
                ''', (new_total_amount, new_paid_amount, new_total_amount - new_paid_amount, self.id))
                
                # Determine new status
                new_balance_amount = new_total_amount - new_paid_amount
                new_status = 'paid' if new_balance_amount <= 0 else ('partial' if new_paid_amount > 0 else 'pending')
                
                cursor.execute('''
                    UPDATE invoices 
                    SET status = ?
                    WHERE id = ?
                ''', (new_status, self.id))
                
                # Create a refund payment record if there's a refund
                refund_amount = current_paid_amount - new_paid_amount
                if refund_amount > 0:
                    from datetime import datetime
                    cursor.execute('''
                        INSERT INTO invoice_payments (
                            invoice_id, amount, payment_method, payment_date, 
                            reference_number, notes, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        self.id, -refund_amount, 'refund', datetime.now().date(),
                        f'RETURN-{datetime.now().strftime("%Y%m%d%H%M%S")}', 
                        f'Refund for returned items: {total_return_amount}', 
                        datetime.now(), datetime.now()
                    ))
                
                conn.commit()
                return total_return_amount
                
            except sqlite3.Error as e:
                conn.rollback()
                raise Exception(f"Database error: {e}")

    def delete(self):
        """Delete invoice and related data"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            try:
                # Delete invoice payments first
                cursor.execute('DELETE FROM invoice_payments WHERE invoice_id = ?', (self.id,))
                
                # Delete invoice items
                cursor.execute('DELETE FROM invoice_items WHERE invoice_id = ?', (self.id,))
                
                # Delete the invoice
                cursor.execute('DELETE FROM invoices WHERE id = ?', (self.id,))
                
                conn.commit()
                return True
            except sqlite3.Error as e:
                conn.rollback()
                raise Exception(f"Database error: {e}")
            finally:
                conn.close()

    def get_customer(self):
        """Get customer details"""
        if not self.customer_id:
            return None
        
        from src.models.customer import Customer
        return Customer.get_by_id(self.customer_id)

    def to_dict(self, include_items=False, include_customer=False, include_payments=False):
        """Convert invoice to dictionary"""
        result = {
            'id': self.id,
            'shop_id': self.shop_id,
            'customer_id': self.customer_id,
            'invoice_number': self.invoice_number,
            'invoice_date': self.invoice_date,
            'due_date': self.due_date,
            'subtotal': float(self.subtotal),
            'tax_amount': float(self.tax_amount),
            'discount_amount': float(self.discount_amount),
            'total_amount': float(self.total_amount),
            'paid_amount': float(self.paid_amount),
            'balance_amount': float(self.balance_amount),
            'status': self.status,
            'notes': self.notes,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'payment_summary': self.get_payment_summary(),
            'days_overdue': self.get_days_overdue()
        }
        
        if include_items:
            items = self.get_items()
            result['items'] = [item.to_dict() for item in items]
        
        if include_customer:
            customer = self.get_customer()
            result['customer'] = customer.to_dict() if customer else None
            
        if include_payments:
            payments = self.get_payments()
            result['payments'] = [payment.to_dict() for payment in payments]
        
        return result

class InvoiceItem:
    def __init__(self, id=None, invoice_id=None, product_id=None, product_name=None, unit=None,
                 quantity=None, unit_price=None, total_price=None, created_at=None):
        self.id = id
        self.invoice_id = invoice_id
        self.product_id = product_id
        self.product_name = product_name
        self.unit = unit
        self.quantity = quantity
        self.unit_price = unit_price
        self.total_price = total_price
        self.created_at = created_at

    def to_dict(self):
        """Convert invoice item to dictionary"""
        return {
            'id': self.id,
            'invoice_id': self.invoice_id,
            'product_id': self.product_id,
            'product_name': self.product_name,
            'unit': self.unit,
            'quantity': float(self.quantity),
            'unit_price': float(self.unit_price),
            'total_price': float(self.total_price),
            'created_at': self.created_at
        }

