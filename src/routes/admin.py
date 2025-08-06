from flask import Blueprint, request, jsonify
from src.routes.auth import require_admin
from src.models.user import User
from src.models.shop import Shop
from src.models.payment import PaymentVerification

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/dashboard', methods=['GET'])
@require_admin
def get_dashboard():
    """Get admin dashboard statistics"""
    try:
        # Get statistics
        total_shops = Shop.count_all()
        active_shops = Shop.count_active()
        total_users = User.count_all()
        pending_verifications = PaymentVerification.count_pending()
        total_revenue = PaymentVerification.get_total_verified_amount()
        
        return jsonify({
            'total_shops': total_shops,
            'active_shops': active_shops,
            'total_users': total_users,
            'pending_verifications': pending_verifications,
            'total_revenue': total_revenue
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/shops', methods=['GET'])
@require_admin
def get_all_shops():
    """Get all shops with pagination"""
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 10))
        search = request.args.get('search', '')
        
        shops = Shop.get_all_paginated(page, limit, search)
        
        return jsonify({
            'shops': [shop.to_dict() for shop in shops],
            'page': page,
            'limit': limit
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/shops/<int:shop_id>/activate', methods=['POST'])
@require_admin
def activate_shop(shop_id):
    """Activate a shop"""
    try:
        shop = Shop.get_by_id(shop_id)
        if not shop:
            return jsonify({'error': 'Shop not found'}), 404
        
        shop.activate()
        
        return jsonify({
            'message': 'Shop activated successfully',
            'shop': shop.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/shops/<int:shop_id>/deactivate', methods=['POST'])
@require_admin
def deactivate_shop(shop_id):
    """Deactivate a shop"""
    try:
        shop = Shop.get_by_id(shop_id)
        if not shop:
            return jsonify({'error': 'Shop not found'}), 404
        
        shop.deactivate()
        
        return jsonify({
            'message': 'Shop deactivated successfully',
            'shop': shop.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/payment-verifications', methods=['GET'])
@require_admin
def get_payment_verifications():
    """Get payment verifications with pagination"""
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 10))
        status = request.args.get('status', '')
        
        verifications = PaymentVerification.get_all_paginated(page, limit, status)
        
        return jsonify({
            'verifications': [v.to_dict() for v in verifications],
            'page': page,
            'limit': limit
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/payment-verifications/<int:verification_id>/verify', methods=['POST'])
@require_admin
def verify_payment(verification_id):
    """Verify a payment"""
    try:
        verification = PaymentVerification.get_by_id(verification_id)
        if not verification:
            return jsonify({'error': 'Payment verification not found'}), 404
        
        data = request.get_json()
        admin_notes = data.get('admin_notes', '')
        
        verification.verify(admin_notes)
        
        return jsonify({
            'message': 'Payment verified successfully',
            'verification': verification.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/payment-verifications/<int:verification_id>/reject', methods=['POST'])
@require_admin
def reject_payment(verification_id):
    """Reject a payment"""
    try:
        verification = PaymentVerification.get_by_id(verification_id)
        if not verification:
            return jsonify({'error': 'Payment verification not found'}), 404
        
        data = request.get_json()
        admin_notes = data.get('admin_notes', '')
        
        verification.reject(admin_notes)
        
        return jsonify({
            'message': 'Payment rejected successfully',
            'verification': verification.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

