import sqlite3
from datetime import datetime
from src.database_sqlite import get_db_connection

class Product:
    def __init__(self, id=None, shop_id=None, name=None, category=None, brand=None,
                 description=None, unit=None, price=None, stock_quantity=0,
                 min_stock_level=0, barcode=None, is_active=True,
                 created_at=None, updated_at=None):
        self.id = id
        self.shop_id = shop_id
        self.name = name
        self.category = category
        self.brand = brand
        self.description = description
        self.unit = unit
        self.price = price
        self.stock_quantity = stock_quantity
        self.min_stock_level = min_stock_level
        self.barcode = barcode
        self.is_active = is_active
        self.created_at = created_at
        self.updated_at = updated_at

    @classmethod
    def create(cls, shop_id, product_data):
        """Create a new product"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO products (
                    shop_id, name, category, brand, description, unit, price,
                    stock_quantity, min_stock_level, barcode
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                shop_id, product_data['name'], product_data['category'],
                product_data.get('brand'), product_data.get('description'),
                product_data['unit'], product_data['price'],
                product_data.get('stock_quantity', 0),
                product_data.get('min_stock_level', 0),
                product_data.get('barcode')
            ))
            conn.commit()
            
            product_id = cursor.lastrowid
            return cls.get_by_id(product_id)

    @classmethod
    def get_by_id(cls, product_id):
        """Get product by ID"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM products WHERE id = ?', (product_id,))
            row = cursor.fetchone()
            
            if row:
                return cls(*row)
            return None

    @classmethod
    def get_by_shop_id(cls, shop_id, limit=None, offset=None, search=None, category=None, active_only=True):
        """Get products by shop ID with optional filtering"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            query = 'SELECT * FROM products WHERE shop_id = ?'
            params = [shop_id]
            
            if active_only:
                query += ' AND is_active = 1'
            
            if search:
                query += ' AND (name LIKE ? OR brand LIKE ? OR barcode LIKE ?)'
                search_term = f'%{search}%'
                params.extend([search_term, search_term, search_term])
            
            if category:
                query += ' AND category = ?'
                params.append(category)
            
            query += ' ORDER BY name ASC'
            
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
    def get_categories(cls, shop_id):
        """Get all product categories for a shop"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT DISTINCT category 
                FROM products 
                WHERE shop_id = ? AND is_active = 1 
                ORDER BY category
            ''', (shop_id,))
            rows = cursor.fetchall()
            
            return [row[0] for row in rows if row[0]]

    @classmethod
    def get_low_stock_products(cls, shop_id):
        """Get products with low stock"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM products 
                WHERE shop_id = ? AND is_active = 1 AND stock_quantity <= min_stock_level
                ORDER BY stock_quantity ASC
            ''', (shop_id,))
            rows = cursor.fetchall()
            
            return [cls(*row) for row in rows]

    @classmethod
    def search_by_barcode(cls, shop_id, barcode):
        """Search product by barcode"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM products 
                WHERE shop_id = ? AND barcode = ? AND is_active = 1
            ''', (shop_id, barcode))
            row = cursor.fetchone()
            
            if row:
                return cls(*row)
            return None

    def update(self, **kwargs):
        """Update product fields"""
        allowed_fields = [
            'name', 'category', 'brand', 'description', 'unit', 'price',
            'stock_quantity', 'min_stock_level', 'barcode', 'is_active'
        ]
        
        update_fields = []
        values = []
        
        for field, value in kwargs.items():
            if field in allowed_fields:
                update_fields.append(f"{field} = ?")
                values.append(value)
        
        if not update_fields:
            return False
        
        values.append(self.id)
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f'''
                UPDATE products 
                SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', values)
            conn.commit()
            return cursor.rowcount > 0

    def update_stock(self, quantity_change):
        """Update stock quantity"""
        new_quantity = max(0, self.stock_quantity + quantity_change)
        return self.update(stock_quantity=new_quantity)

    def deactivate(self):
        """Deactivate product"""
        return self.update(is_active=False)

    def activate(self):
        """Activate product"""
        return self.update(is_active=True)

    def is_low_stock(self):
        """Check if product is low on stock"""
        return self.stock_quantity <= self.min_stock_level

    def to_dict(self):
        """Convert product to dictionary"""
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
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

