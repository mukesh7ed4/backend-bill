from flask import Blueprint, request, jsonify
from src.routes.auth import require_shop_user, get_current_shop_id
from src.models.payment import PaymentVerification

payment_bp = Blueprint('payment', __name__)

@payment_bp.route('/pricing', methods=['GET'])
def get_pricing():
    """Get pricing information"""
    return jsonify({
        'plans': [
            {
                'name': 'Basic',
                'price': 999,
                'currency': 'INR',
                'duration': 'monthly',
                'features': [
                    'Up to 100 customers',
                    'Up to 500 products',
                    'Unlimited invoices',
                    'Basic reporting',
                    'Email support'
                ]
            },
            {
                'name': 'Pro',
                'price': 1999,
                'currency': 'INR',
                'duration': 'monthly',
                'features': [
                    'Up to 500 customers',
                    'Up to 2000 products',
                    'Unlimited invoices',
                    'Advanced reporting',
                    'Priority support',
                    'Inventory management',
                    'Payment tracking'
                ]
            },
            {
                'name': 'Enterprise',
                'price': 4999,
                'currency': 'INR',
                'duration': 'monthly',
                'features': [
                    'Unlimited customers',
                    'Unlimited products',
                    'Unlimited invoices',
                    'Advanced analytics',
                    '24/7 support',
                    'Multi-location support',
                    'API access',
                    'Custom integrations'
                ]
            }
        ]
    }), 200

@payment_bp.route('/submit', methods=['POST'])
@require_shop_user
def submit_payment():
    """Submit payment for verification"""
    try:
        shop_id = get_current_shop_id()
        if not shop_id:
            return jsonify({'error': 'Shop not found'}), 404
        
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['amount', 'payment_method']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400
        
        if data['amount'] <= 0:
            return jsonify({'error': 'Payment amount must be positive'}), 400
        
        verification = PaymentVerification.create(shop_id, data)
        
        return jsonify({
            'message': 'Payment submitted for verification',
            'verification': verification.to_dict()
        }), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@payment_bp.route('/subscription-status', methods=['GET'])
@require_shop_user
def get_subscription_status():
    """Get subscription status"""
    try:
        shop_id = get_current_shop_id()
        if not shop_id:
            return jsonify({'error': 'Shop not found'}), 404
        
        from src.models.shop import Shop
        shop = Shop.get_by_id(shop_id)
        if not shop:
            return jsonify({'error': 'Shop not found'}), 404
        
        # Get payment verifications
        verifications = PaymentVerification.get_by_shop_id(shop_id)
        
        return jsonify({
            'subscription_status': shop.subscription_status,
            'is_active': shop.is_active,
            'verifications': [v.to_dict() for v in verifications]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@payment_bp.route('/methods', methods=['GET'])
def get_payment_methods():
    """Get available payment methods"""
    return jsonify({
        'methods': [
            {
                'id': 'upi',
                'name': 'UPI',
                'description': 'Pay using UPI apps like PhonePe, Google Pay, Paytm',
                'instructions': 'Send payment to UPI ID: billing@shop.com and upload screenshot'
            },
            {
                'id': 'bank_transfer',
                'name': 'Bank Transfer',
                'description': 'Direct bank transfer',
                'instructions': 'Transfer to Account: 1234567890, IFSC: BANK0001234'
            },
            {
                'id': 'card',
                'name': 'Credit/Debit Card',
                'description': 'Pay using credit or debit card',
                'instructions': 'Card payments will be processed securely'
            },
            {
                'id': 'cash',
                'name': 'Cash',
                'description': 'Cash payment at office',
                'instructions': 'Visit our office for cash payment'
            }
        ]
    }), 200

