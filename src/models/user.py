import bcrypt
from datetime import datetime
from src.database import db

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @classmethod
    def create(cls, user_data):
        """Create a new user"""
        # Hash the password
        password_hash = bcrypt.hashpw(user_data['password'].encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        user = cls(
            username=user_data['username'],
            email=user_data['email'],
            password_hash=password_hash,
            is_admin=user_data.get('is_admin', False)
        )
        db.session.add(user)
        db.session.commit()
        return user

    @classmethod
    def get_by_id(cls, user_id):
        return cls.query.get(user_id)

    @classmethod
    def get_by_username(cls, username):
        return cls.query.filter_by(username=username).first()

    @classmethod
    def get_by_email(cls, email):
        return cls.query.filter_by(email=email).first()

    @classmethod
    def count_all(cls):
        return cls.query.count()

    @classmethod
    def authenticate(cls, username, password):
        """Authenticate user with username and password"""
        user = cls.get_by_username(username)
        if user and user.check_password(password):
            return user
        return None

    def check_password(self, password):
        """Check if the provided password matches the stored hash"""
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))

    def update(self, **kwargs):
        """Update user fields"""
        for key, value in kwargs.items():
            if hasattr(self, key) and key != 'password':
                setattr(self, key, value)
        db.session.commit()

    def update_password(self, new_password):
        """Update user password"""
        self.password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        db.session.commit()

    @classmethod
    def create_admin_user(cls):
        """Create admin user if it doesn't exist"""
        admin = cls.get_by_username('admin')
        if not admin:
            admin_data = {
                'username': 'admin',
                'email': 'admin@billing.com',
                'password': 'admin123',
                'is_admin': True
            }
            admin = cls.create(admin_data)
            return admin
        return None

    def to_dict(self):
        """Convert user to dictionary"""
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
            'username': self.username,
            'email': self.email,
            'is_admin': self.is_admin,
            'created_at': format_datetime(self.created_at),
            'updated_at': format_datetime(self.updated_at)
        }

