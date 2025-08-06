from src.database_sqlite import get_db_connection
from datetime import datetime

class Expense:
    def __init__(self, id=None, shop_id=None, title=None, description=None, amount=None, 
                 category=None, expense_date=None, payment_method=None, reference_number=None, 
                 notes=None, created_at=None, updated_at=None):
        self.id = id
        self.shop_id = shop_id
        self.title = title
        self.description = description
        self.amount = amount
        self.category = category
        self.expense_date = expense_date
        self.payment_method = payment_method
        self.reference_number = reference_number
        self.notes = notes
        self.created_at = created_at
        self.updated_at = updated_at

    @classmethod
    def create(cls, shop_id, expense_data):
        """Create a new expense"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            query = '''
                INSERT INTO expenses (
                    shop_id, title, description, amount, category, expense_date,
                    payment_method, reference_number, notes, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            '''
            
            now = datetime.now().isoformat()
            cursor.execute(query, (
                shop_id,
                expense_data['title'],
                expense_data.get('description', ''),
                expense_data['amount'],
                expense_data['category'],
                expense_data['expense_date'],
                expense_data.get('payment_method', 'cash'),
                expense_data.get('reference_number', ''),
                expense_data.get('notes', ''),
                now,
                now
            ))
            
            expense_id = cursor.lastrowid
            conn.commit()
            
            return cls.get_by_id(expense_id)

    @classmethod
    def get_by_id(cls, expense_id):
        """Get expense by ID"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM expenses WHERE id = ?
            ''', (expense_id,))
            row = cursor.fetchone()
            
            if row:
                return cls(*row)
            return None

    @classmethod
    def get_by_shop_id(cls, shop_id, limit=None, offset=None, category=None, search=None, sort='latest', date_filter=None):
        """Get expenses by shop ID with optional filtering and sorting"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            query = '''
                SELECT * FROM expenses WHERE shop_id = ?
            '''
            params = [shop_id]
            
            if category:
                query += ' AND category = ?'
                params.append(category)
            
            if search:
                query += ' AND (title LIKE ? OR description LIKE ?)'
                search_term = f'%{search}%'
                params.extend([search_term, search_term])
            
            # Handle specific date filter
            if date_filter:
                query += ' AND DATE(expense_date) = ?'
                params.append(date_filter)
            
            # Handle sorting
            if sort == 'latest':
                query += ' ORDER BY expense_date DESC, created_at DESC'
            elif sort == 'oldest':
                query += ' ORDER BY expense_date ASC, created_at ASC'
            elif sort == 'amount_high':
                query += ' ORDER BY amount DESC'
            elif sort == 'amount_low':
                query += ' ORDER BY amount ASC'
            else:
                query += ' ORDER BY expense_date DESC'
            
            if limit:
                query += ' LIMIT ?'
                params.append(limit)
                if offset:
                    query += ' OFFSET ?'
                    params.append(offset)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            return [cls(*row) for row in rows]

    def delete(self):
        """Delete expense"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM expenses WHERE id = ?', (self.id,))
            conn.commit()

    def to_dict(self):
        """Convert expense to dictionary"""
        return {
            'id': self.id,
            'shop_id': self.shop_id,
            'title': self.title,
            'description': self.description,
            'amount': self.amount,
            'category': self.category,
            'expense_date': self.expense_date,
            'payment_method': self.payment_method,
            'reference_number': self.reference_number,
            'notes': self.notes,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        } 