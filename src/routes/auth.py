from flask import Blueprint, request, jsonify, session
from src.models.user import User
from src.models.shop import Shop

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['POST'])
def login():
    """User login"""
    try:
        data = request.get_json()
        username_or_email = data.get('username') or data.get('email')
        password = data.get('password')
        
        if not username_or_email or not password:
            return jsonify({'error': 'Username/email and password are required'}), 400
        
        # Authenticate user
        user = User.authenticate(username_or_email, password)
        if not user:
            return jsonify({'error': 'Invalid credentials'}), 401
        
        # Store user in session
        session['user_id'] = user.id
        session['user_role'] = user.role
        
        # Get shop data if user is shop_user
        shop = None
        if user.role == 'shop_user':
            shop = Shop.get_by_user_id(user.id)
        
        return jsonify({
            'message': 'Login successful',
            'user': user.to_dict(),
            'shop': shop.to_dict() if shop else None
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/logout', methods=['POST'])
def logout():
    """User logout"""
    session.clear()
    return jsonify({'message': 'Logout successful'}), 200

@auth_bp.route('/register-shop', methods=['POST'])
def register_shop():
    """Register new shop"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['username', 'email', 'password', 'shop_name', 'owner_name', 'phone', 'address', 'city', 'state', 'pincode']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400
        
        # Create user
        user_data = {
            'username': data['username'],
            'email': data['email'],
            'password': data['password'],
            'role': 'shop_user'
        }
        user = User.create(user_data)
        
        # Create shop
        shop_data = {
            'shop_name': data['shop_name'],
            'owner_name': data['owner_name'],
            'phone': data['phone'],
            'email': data['email'],
            'address': data['address'],
            'city': data['city'],
            'state': data['state'],
            'pincode': data['pincode'],
            'gst_number': data.get('gst_number'),
            'license_number': data.get('license_number')
        }
        
        shop = Shop.create(user.id, shop_data)
        
        return jsonify({
            'message': 'Shop registered successfully',
            'user': user.to_dict(),
            'shop': shop.to_dict()
        }), 201
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/me', methods=['GET'])
def get_current_user():
    """Get current user information"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'Not authenticated'}), 401
        
        user = User.get_by_id(user_id)
        if not user:
            session.clear()
            return jsonify({'error': 'User not found'}), 401
        
        # Get shop data if user is shop_user
        shop = None
        if user.role == 'shop_user':
            shop = Shop.get_by_user_id(user.id)
        
        return jsonify({
            'user': user.to_dict(),
            'shop': shop.to_dict() if shop else None
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/change-password', methods=['POST'])
def change_password():
    """Change user password"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'Not authenticated'}), 401
        
        data = request.get_json()
        current_password = data.get('current_password')
        new_password = data.get('new_password')
        
        if not current_password or not new_password:
            return jsonify({'error': 'Current password and new password are required'}), 400
        
        user = User.get_by_id(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Verify current password
        if not user.check_password(current_password):
            return jsonify({'error': 'Current password is incorrect'}), 400
        
        # Change password
        user.update_password(new_password)
        return jsonify({'message': 'Password changed successfully'}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Authentication decorator
def require_auth(f):
    """Decorator to require authentication"""
    def decorated_function(*args, **kwargs):
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

def require_admin(f):
    """Decorator to require admin role"""
    def decorated_function(*args, **kwargs):
        user_id = session.get('user_id')
        user_role = session.get('user_role')
        if not user_id or user_role != 'admin':
            return jsonify({'error': 'Admin access required'}), 403
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

def require_shop_user(f):
    """Decorator to require shop user role"""
    def decorated_function(*args, **kwargs):
        user_id = session.get('user_id')
        user_role = session.get('user_role')
        if not user_id or user_role != 'shop_user':
            return jsonify({'error': 'Shop user access required'}), 403
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

def get_current_user_id():
    """Get current user ID from session"""
    return session.get('user_id')

def get_current_shop_id():
    """Get current shop ID from session"""
    user_id = session.get('user_id')
    if user_id:
        shop = Shop.get_by_user_id(user_id)
        return shop.id if shop else None
    return None

