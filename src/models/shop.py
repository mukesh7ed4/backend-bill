import sqlite3
from datetime import datetime
from src.database_postgresql import get_db_connection

class Shop:
    def __init__(self, id=None, user_id=None, shop_name=None, owner_name=None, 
                 phone=None, address=None, city=None, state=None, pincode=None,
                 gst_number=None, license_number=None, is_active=False, 
                 subscription_status='inactive', created_at=None, updated_at=None):
        self.id = id
        self.user_id = user_id
        self.shop_name = shop_name
        self.owner_name = owner_name
        self.phone = phone
        self.address = address
        self.city = city
        self.state = state
        self.pincode = pincode
        self.gst_number = gst_number
        self.license_number = license_number
        self.is_active = is_active
        self.subscription_status = subscription_status
        self.created_at = created_at
        self.updated_at = updated_at

    @classmethod
    def create(cls, user_id, shop_data):
        """Create a new shop"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO shops (
                    user_id, shop_name, owner_name, phone, address, city, state, 
                    pincode, gst_number, license_number, is_active, subscription_status,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_id, shop_data.get('shop_name'), shop_data.get('owner_name'),
                shop_data.get('phone'), shop_data.get('address'), shop_data.get('city'),
                shop_data.get('state'), shop_data.get('pincode'), shop_data.get('gst_number'),
                shop_data.get('license_number'), False, 'inactive',
                datetime.now(), datetime.now()
            ))
            
            shop_id = cursor.lastrowid
            conn.commit()
            
            return cls.get_by_id(shop_id)
            
        except sqlite3.Error as e:
            conn.rollback()
            raise Exception(f"Database error: {e}")
        finally:
            conn.close()

    @classmethod
    def get_by_id(cls, shop_id):
        """Get shop by ID"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT * FROM shops WHERE id = ?', (shop_id,))
            row = cursor.fetchone()
            
            if row:
                return cls(*row)
            return None
            
        except sqlite3.Error as e:
            raise Exception(f"Database error: {e}")
        finally:
            conn.close()

    @classmethod
    def get_by_user_id(cls, user_id):
        """Get shop by user ID"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT * FROM shops WHERE user_id = ?', (user_id,))
            row = cursor.fetchone()
            
            if row:
                return cls(*row)
            return None
            
        except sqlite3.Error as e:
            raise Exception(f"Database error: {e}")
        finally:
            conn.close()

    @classmethod
    def get_all_paginated(cls, page=1, limit=10, search=''):
        """Get all shops with pagination and search"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            offset = (page - 1) * limit
            
            if search:
                cursor.execute('''
                    SELECT s.*, u.email FROM shops s
                    LEFT JOIN users u ON s.user_id = u.id
                    WHERE s.shop_name LIKE ? OR s.owner_name LIKE ? OR u.email LIKE ?
                    ORDER BY s.created_at DESC
                    LIMIT ? OFFSET ?
                ''', (f'%{search}%', f'%{search}%', f'%{search}%', limit, offset))
            else:
                cursor.execute('''
                    SELECT s.*, u.email FROM shops s
                    LEFT JOIN users u ON s.user_id = u.id
                    ORDER BY s.created_at DESC
                    LIMIT ? OFFSET ?
                ''', (limit, offset))
            
            rows = cursor.fetchall()
            shops = []
            
            for row in rows:
                shop = cls(*row[:-1])  # Exclude email from shop object
                shop.email = row[-1]   # Add email as separate attribute
                shops.append(shop)
            
            return shops
            
        except sqlite3.Error as e:
            raise Exception(f"Database error: {e}")
        finally:
            conn.close()

    @classmethod
    def count_all(cls):
        """Count all shops"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT COUNT(*) FROM shops')
            return cursor.fetchone()[0]
            
        except sqlite3.Error as e:
            raise Exception(f"Database error: {e}")
        finally:
            conn.close()

    @classmethod
    def count_active(cls):
        """Count active shops"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT COUNT(*) FROM shops WHERE is_active = 1')
            return cursor.fetchone()[0]
            
        except sqlite3.Error as e:
            raise Exception(f"Database error: {e}")
        finally:
            conn.close()

    def activate(self):
        """Activate the shop"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                UPDATE shops 
                SET is_active = 1, subscription_status = 'active', updated_at = ?
                WHERE id = ?
            ''', (datetime.now(), self.id))
            
            conn.commit()
            self.is_active = True
            self.subscription_status = 'active'
            
        except sqlite3.Error as e:
            conn.rollback()
            raise Exception(f"Database error: {e}")
        finally:
            conn.close()

    def deactivate(self):
        """Deactivate the shop"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                UPDATE shops 
                SET is_active = 0, subscription_status = 'inactive', updated_at = ?
                WHERE id = ?
            ''', (datetime.now(), self.id))
            
            conn.commit()
            self.is_active = False
            self.subscription_status = 'inactive'
            
        except sqlite3.Error as e:
            conn.rollback()
            raise Exception(f"Database error: {e}")
        finally:
            conn.close()

    def update(self, shop_data):
        """Update shop information"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                UPDATE shops 
                SET shop_name = ?, owner_name = ?, phone = ?, address = ?, 
                    city = ?, state = ?, pincode = ?, gst_number = ?, 
                    license_number = ?, updated_at = ?
                WHERE id = ?
            ''', (
                shop_data.get('shop_name', self.shop_name),
                shop_data.get('owner_name', self.owner_name),
                shop_data.get('phone', self.phone),
                shop_data.get('address', self.address),
                shop_data.get('city', self.city),
                shop_data.get('state', self.state),
                shop_data.get('pincode', self.pincode),
                shop_data.get('gst_number', self.gst_number),
                shop_data.get('license_number', self.license_number),
                datetime.now(),
                self.id
            ))
            
            conn.commit()
            
            # Update instance attributes
            for key, value in shop_data.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            
        except sqlite3.Error as e:
            conn.rollback()
            raise Exception(f"Database error: {e}")
        finally:
            conn.close()

    def get_dashboard_stats(self):
        """Get dashboard statistics for the shop"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Get total customers
            cursor.execute('SELECT COUNT(*) FROM customers WHERE shop_id = ?', (self.id,))
            total_customers = cursor.fetchone()[0]
            
            # Get total products
            cursor.execute('SELECT COUNT(*) FROM products WHERE shop_id = ? AND is_active = 1', (self.id,))
            total_products = cursor.fetchone()[0]
            
            # Get total invoices
            cursor.execute('SELECT COUNT(*) FROM invoices WHERE shop_id = ?', (self.id,))
            total_invoices = cursor.fetchone()[0]
            
            # Get total revenue (sum of total_amount from invoices)
            cursor.execute('SELECT COALESCE(SUM(total_amount), 0) FROM invoices WHERE shop_id = ?', (self.id,))
            total_revenue = cursor.fetchone()[0] or 0
            
            # Get today's sales
            cursor.execute('''
                SELECT COALESCE(SUM(total_amount), 0) FROM invoices 
                WHERE shop_id = ? AND DATE(invoice_date) = DATE('now')
            ''', (self.id,))
            todays_sales = cursor.fetchone()[0] or 0
            
            # Get monthly sales (current month)
            cursor.execute('''
                SELECT COALESCE(SUM(total_amount), 0) FROM invoices 
                WHERE shop_id = ? AND strftime('%Y-%m', invoice_date) = strftime('%Y-%m', 'now')
            ''', (self.id,))
            monthly_sales = cursor.fetchone()[0] or 0
            
            # Get low stock products
            cursor.execute('''
                SELECT COUNT(*) FROM products 
                WHERE shop_id = ? AND is_active = 1 AND stock_quantity <= min_stock_level
            ''', (self.id,))
            low_stock_products = cursor.fetchone()[0]
            
            return {
                'total_customers': total_customers,
                'total_products': total_products,
                'total_invoices': total_invoices,
                'total_revenue': float(total_revenue),
                'todays_sales': float(todays_sales),
                'monthly_sales': float(monthly_sales),
                'low_stock_products': low_stock_products
            }
            
        except sqlite3.Error as e:
            raise Exception(f"Database error: {e}")
        finally:
            conn.close()

    def to_dict(self):
        """Convert shop to dictionary"""
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

