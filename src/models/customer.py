import psycopg2
from datetime import datetime
from src.database_postgresql import get_db_connection

class Customer:
    def __init__(self, id=None, shop_id=None, name=None, phone=None, email=None,
                 address=None, city=None, state=None, pincode=None, gst_number=None,
                 created_at=None, updated_at=None):
        self.id = id
        self.shop_id = shop_id
        self.name = name
        self.phone = phone
        self.email = email
        self.address = address
        self.city = city
        self.state = state
        self.pincode = pincode
        self.gst_number = gst_number
        self.created_at = created_at
        self.updated_at = updated_at

    @classmethod
    def create(cls, shop_id, customer_data):
        """Create a new customer"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO customers (
                    shop_id, name, phone, email, address, city, state, pincode, gst_number
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (
                shop_id, customer_data['name'], customer_data.get('phone'),
                customer_data.get('email'), customer_data.get('address'),
                customer_data.get('city'), customer_data.get('state'),
                customer_data.get('pincode'), customer_data.get('gst_number')
            ))
            conn.commit()
            
            customer_id = cursor.lastrowid
            return cls.get_by_id(customer_id)

    @classmethod
    def get_by_id(cls, customer_id):
        """Get customer by ID"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM customers WHERE id = %s', (customer_id,))
            row = cursor.fetchone()
            
            if row:
                return cls(*row)
            return None

    @classmethod
    def get_by_shop_id(cls, shop_id, limit=None, offset=None, search=None):
        """Get customers by shop ID with optional search"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            query = 'SELECT * FROM customers WHERE shop_id = %s'
            params = [shop_id]
            
            if search:
                query += ' AND (name LIKE %s OR phone LIKE %s OR email LIKE %s)'
                search_term = f'%{search}%'
                params.extend([search_term, search_term, search_term])
            
            query += ' ORDER BY name ASC'
            
            if limit:
                query += ' LIMIT %s'
                params.append(limit)
                if offset:
                    query += ' OFFSET %s'
                    params.append(offset)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            return [cls(*row) for row in rows]

    @classmethod
    def search_by_phone(cls, shop_id, phone):
        """Search customer by phone number"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM customers 
                WHERE shop_id = %s AND phone LIKE %s
            ''', (shop_id, f'%{phone}%'))
            rows = cursor.fetchall()
            
            return [cls(*row) for row in rows]

    def update(self, **kwargs):
        """Update customer fields"""
        allowed_fields = [
            'name', 'phone', 'email', 'address', 'city', 
            'state', 'pincode', 'gst_number'
        ]
        
        update_fields = []
        values = []
        
        for field, value in kwargs.items():
            if field in allowed_fields:
                update_fields.append(f"{field} = %s")
                values.append(value)
        
        if not update_fields:
            return False
        
        values.append(self.id)
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f'''
                UPDATE customers 
                SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            ''', values)
            conn.commit()
            return cursor.rowcount > 0

    def delete(self):
        """Delete customer"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM customers WHERE id = %s', (self.id,))
            conn.commit()
            return cursor.rowcount > 0

    def get_invoices(self, limit=None):
        """Get customer's invoices"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            query = '''
                SELECT * FROM invoices 
                WHERE customer_id = %s 
                ORDER BY invoice_date DESC
            '''
            params = [self.id]
            
            if limit:
                query += ' LIMIT %s'
                params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            from src.models.invoice import Invoice
            return [Invoice(*row) for row in rows]

    def get_total_purchases(self):
        """Get total purchase amount for customer"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT COALESCE(SUM(total_amount), 0) 
                FROM invoices 
                WHERE customer_id = %s
            ''', (self.id,))
            return float(cursor.fetchone()[0])

    def get_outstanding_balance(self):
        """Get outstanding balance for customer"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT COALESCE(SUM(balance_amount), 0) 
                FROM invoices 
                WHERE customer_id = %s AND balance_amount > 0
            ''', (self.id,))
            return float(cursor.fetchone()[0])

    def get_recent_payments(self, limit=10):
        """Get recent payments for this customer"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT ip.*, i.invoice_number, i.invoice_date
                FROM invoice_payments ip
                JOIN invoices i ON ip.invoice_id = i.id
                WHERE i.customer_id = %s
                ORDER BY ip.payment_date DESC, ip.created_at DESC
                LIMIT %s
            ''', (self.id, limit))
            
            rows = cursor.fetchall()
            payments = []
            
            for row in rows:
                payments.append({
                    'id': row[0],
                    'invoice_id': row[1],
                    'amount': float(row[2]),
                    'payment_method': row[3],
                    'payment_date': row[4],
                    'reference_number': row[5],
                    'notes': row[6],
                    'created_at': row[7],
                    'updated_at': row[8],
                    'invoice_number': row[9],
                    'invoice_date': row[10]
                })
            
            return payments

    def to_dict(self):
        """Convert customer to dictionary"""
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
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

