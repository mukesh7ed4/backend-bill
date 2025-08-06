import psycopg2
import bcrypt
from datetime import datetime
from src.database_postgresql import get_db_connection

# Initialize database connection for SQLAlchemy-like usage
class User:
    def __init__(self, id=None, username=None, email=None, password_hash=None,
                 role='shop_user', is_active=True, created_at=None, updated_at=None):
        self.id = id
        self.username = username
        self.email = email
        self.password_hash = password_hash
        self.role = role
        self.is_active = is_active
        self.created_at = created_at
        self.updated_at = updated_at

    @classmethod
    def create(cls, user_data):
        """Create a new user"""
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            # Hash password
            password_hash = bcrypt.hashpw(
                user_data['password'].encode('utf-8'), 
                bcrypt.gensalt()
            ).decode('utf-8')
            cursor.execute('''
                INSERT INTO users (username, email, password_hash, role, is_active, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            ''', (
                user_data['username'], user_data['email'], password_hash,
                user_data.get('role', 'shop_user'), True, datetime.now(), datetime.now()
            ))
            user_id = cursor.fetchone()[0]
            conn.commit()
            return cls.get_by_id(user_id)
        except psycopg2.Error as e:
            conn.rollback()
            raise Exception(f"Database error: {e}")
        finally:
            conn.close()

    @classmethod
    def get_by_id(cls, user_id):
        """Get user by ID"""
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))
            row = cursor.fetchone()
            if row:
                return cls(*row)
            return None
        except psycopg2.Error as e:
            raise Exception(f"Database error: {e}")
        finally:
            conn.close()

    @classmethod
    def get_by_username(cls, username):
        """Get user by username"""
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
            row = cursor.fetchone()
            if row:
                return cls(*row)
            return None
        except psycopg2.Error as e:
            raise Exception(f"Database error: {e}")
        finally:
            conn.close()

    @classmethod
    def get_by_email(cls, email):
        """Get user by email"""
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
            row = cursor.fetchone()
            if row:
                return cls(*row)
            return None
        except psycopg2.Error as e:
            raise Exception(f"Database error: {e}")
        finally:
            conn.close()

    @classmethod
    def get_by_username_or_email(cls, identifier):
        """Get user by username or email"""
        user = cls.get_by_username(identifier)
        if not user:
            user = cls.get_by_email(identifier)
        return user

    @classmethod
    def authenticate(cls, username_or_email, password):
        """Authenticate user with username/email and password"""
        user = cls.get_by_username_or_email(username_or_email)
        if user and user.is_active and user.check_password(password):
            return user
        return None

    @classmethod
    def count_all(cls):
        """Count all users"""
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT COUNT(*) FROM users')
            return cursor.fetchone()[0]
        except psycopg2.Error as e:
            raise Exception(f"Database error: {e}")
        finally:
            conn.close()

    @classmethod
    def create_admin_user(cls):
        """Create default admin user if not exists"""
        admin = cls.get_by_username('admin')
        if admin:
            return None
        admin_data = {
            'username': 'admin',
            'email': 'admin@billing.com',
            'password': 'admin123',
            'role': 'admin'
        }
        return cls.create(admin_data)

    def check_password(self, password):
        """Check if password matches"""
        return bcrypt.checkpw(
            password.encode('utf-8'), 
            self.password_hash.encode('utf-8')
        )

    def update_password(self, new_password):
        """Update user password"""
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            password_hash = bcrypt.hashpw(
                new_password.encode('utf-8'), 
                bcrypt.gensalt()
            ).decode('utf-8')
            cursor.execute('''
                UPDATE users 
                SET password_hash = %s, updated_at = %s
                WHERE id = %s
            ''', (password_hash, datetime.now(), self.id))
            conn.commit()
            self.password_hash = password_hash
        except psycopg2.Error as e:
            conn.rollback()
            raise Exception(f"Database error: {e}")
        finally:
            conn.close()

    def update(self, user_data):
        """Update user information"""
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                UPDATE users 
                SET username = %s, email = %s, updated_at = %s
                WHERE id = %s
            ''', (
                user_data.get('username', self.username),
                user_data.get('email', self.email),
                datetime.now(),
                self.id
            ))
            conn.commit()
            self.username = user_data.get('username', self.username)
            self.email = user_data.get('email', self.email)
        except psycopg2.Error as e:
            conn.rollback()
            raise Exception(f"Database error: {e}")
        finally:
            conn.close()

    def to_dict(self):
        """Convert user to dictionary"""
        def format_datetime(dt):
            if isinstance(dt, str):
                return dt
            if dt is None:
                return None
            return dt.isoformat()
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'is_active': self.is_active,
            'created_at': format_datetime(self.created_at),
            'updated_at': format_datetime(self.updated_at)
        }

