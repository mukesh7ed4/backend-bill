import sqlite3
from datetime import datetime
from src.database_postgresql import get_db_connection

class PaymentVerification:
    def __init__(self, id=None, shop_id=None, amount=None, payment_method=None,
                 reference_number=None, payment_proof=None, status='pending',
                 admin_notes=None, created_at=None, updated_at=None):
        self.id = id
        self.shop_id = shop_id
        self.amount = amount
        self.payment_method = payment_method
        self.reference_number = reference_number
        self.payment_proof = payment_proof
        self.status = status
        self.admin_notes = admin_notes
        self.created_at = created_at
        self.updated_at = updated_at

    @classmethod
    def create(cls, shop_id, payment_data):
        """Create a new payment verification"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO payment_verifications (
                    shop_id, amount, payment_method, reference_number, 
                    payment_proof, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                shop_id, payment_data.get('amount'), payment_data.get('payment_method'),
                payment_data.get('reference_number'), payment_data.get('payment_proof'),
                'pending', datetime.now(), datetime.now()
            ))
            
            verification_id = cursor.lastrowid
            conn.commit()
            
            return cls.get_by_id(verification_id)
            
        except sqlite3.Error as e:
            conn.rollback()
            raise Exception(f"Database error: {e}")
        finally:
            conn.close()

    @classmethod
    def get_by_id(cls, verification_id):
        """Get payment verification by ID"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT * FROM payment_verifications WHERE id = ?', (verification_id,))
            row = cursor.fetchone()
            
            if row:
                return cls(*row)
            return None
            
        except sqlite3.Error as e:
            raise Exception(f"Database error: {e}")
        finally:
            conn.close()

    @classmethod
    def get_by_shop_id(cls, shop_id):
        """Get payment verifications by shop ID"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT * FROM payment_verifications 
                WHERE shop_id = ? 
                ORDER BY created_at DESC
            ''', (shop_id,))
            
            rows = cursor.fetchall()
            return [cls(*row) for row in rows]
            
        except sqlite3.Error as e:
            raise Exception(f"Database error: {e}")
        finally:
            conn.close()

    @classmethod
    def get_all_paginated(cls, page=1, limit=10, status=''):
        """Get all payment verifications with pagination"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            offset = (page - 1) * limit
            
            if status:
                cursor.execute('''
                    SELECT pv.*, s.shop_name FROM payment_verifications pv
                    LEFT JOIN shops s ON pv.shop_id = s.id
                    WHERE pv.status = ?
                    ORDER BY pv.created_at DESC
                    LIMIT ? OFFSET ?
                ''', (status, limit, offset))
            else:
                cursor.execute('''
                    SELECT pv.*, s.shop_name FROM payment_verifications pv
                    LEFT JOIN shops s ON pv.shop_id = s.id
                    ORDER BY pv.created_at DESC
                    LIMIT ? OFFSET ?
                ''', (limit, offset))
            
            rows = cursor.fetchall()
            verifications = []
            
            for row in rows:
                verification = cls(*row[:-1])  # Exclude shop_name from verification object
                verification.shop = {'shop_name': row[-1]}  # Add shop info
                verifications.append(verification)
            
            return verifications
            
        except sqlite3.Error as e:
            raise Exception(f"Database error: {e}")
        finally:
            conn.close()

    @classmethod
    def count_pending(cls):
        """Count pending payment verifications"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT COUNT(*) FROM payment_verifications WHERE status = ?', ('pending',))
            return cursor.fetchone()[0]
            
        except sqlite3.Error as e:
            raise Exception(f"Database error: {e}")
        finally:
            conn.close()

    @classmethod
    def get_total_verified_amount(cls):
        """Get total amount of verified payments"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT SUM(amount) FROM payment_verifications WHERE status = ?', ('verified',))
            result = cursor.fetchone()[0]
            return result if result else 0
            
        except sqlite3.Error as e:
            raise Exception(f"Database error: {e}")
        finally:
            conn.close()

    def verify(self, admin_notes=''):
        """Verify the payment"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                UPDATE payment_verifications 
                SET status = 'verified', admin_notes = ?, updated_at = ?
                WHERE id = ?
            ''', (admin_notes, datetime.now(), self.id))
            
            conn.commit()
            self.status = 'verified'
            self.admin_notes = admin_notes
            
        except sqlite3.Error as e:
            conn.rollback()
            raise Exception(f"Database error: {e}")
        finally:
            conn.close()

    def reject(self, admin_notes=''):
        """Reject the payment"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                UPDATE payment_verifications 
                SET status = 'rejected', admin_notes = ?, updated_at = ?
                WHERE id = ?
            ''', (admin_notes, datetime.now(), self.id))
            
            conn.commit()
            self.status = 'rejected'
            self.admin_notes = admin_notes
            
        except sqlite3.Error as e:
            conn.rollback()
            raise Exception(f"Database error: {e}")
        finally:
            conn.close()

    def to_dict(self):
        """Convert payment verification to dictionary"""
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
            'amount': self.amount,
            'payment_method': self.payment_method,
            'reference_number': self.reference_number,
            'payment_proof': self.payment_proof,
            'status': self.status,
            'admin_notes': self.admin_notes,
            'created_at': format_datetime(self.created_at),
            'updated_at': format_datetime(self.updated_at),
            'shop': getattr(self, 'shop', None)  # Include shop info if available
        }


class InvoicePayment:
    def __init__(self, id=None, invoice_id=None, amount=None, payment_method=None,
                 payment_date=None, reference_number=None, notes=None,
                 created_at=None, updated_at=None):
        self.id = id
        self.invoice_id = invoice_id
        self.amount = amount
        self.payment_method = payment_method
        self.payment_date = payment_date
        self.reference_number = reference_number
        self.notes = notes
        self.created_at = created_at
        self.updated_at = updated_at

    @classmethod
    def create(cls, invoice_id, payment_data):
        """Create a new invoice payment"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO invoice_payments (
                    invoice_id, amount, payment_method, payment_date,
                    reference_number, notes, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                invoice_id, payment_data.get('amount'), payment_data.get('payment_method'),
                payment_data.get('payment_date'), payment_data.get('reference_number'),
                payment_data.get('notes'), datetime.now(), datetime.now()
            ))
            
            payment_id = cursor.lastrowid
            conn.commit()
            
            return cls.get_by_id(payment_id)
            
        except sqlite3.Error as e:
            conn.rollback()
            raise Exception(f"Database error: {e}")
        finally:
            conn.close()

    @classmethod
    def get_by_id(cls, payment_id):
        """Get invoice payment by ID"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT * FROM invoice_payments WHERE id = ?', (payment_id,))
            row = cursor.fetchone()
            
            if row:
                return cls(*row)
            return None
            
        except sqlite3.Error as e:
            raise Exception(f"Database error: {e}")
        finally:
            conn.close()

    @classmethod
    def get_by_invoice_id(cls, invoice_id):
        """Get payments by invoice ID"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT * FROM invoice_payments 
                WHERE invoice_id = ? 
                ORDER BY payment_date DESC
            ''', (invoice_id,))
            
            rows = cursor.fetchall()
            return [cls(*row) for row in rows]
            
        except sqlite3.Error as e:
            raise Exception(f"Database error: {e}")
        finally:
            conn.close()

    def to_dict(self):
        """Convert invoice payment to dictionary"""
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
            'amount': self.amount,
            'payment_method': self.payment_method,
            'payment_date': format_datetime(self.payment_date),
            'reference_number': self.reference_number,
            'notes': self.notes,
            'created_at': format_datetime(self.created_at),
            'updated_at': format_datetime(self.updated_at)
        }

