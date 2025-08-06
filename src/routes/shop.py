from flask import Blueprint, request, jsonify
from src.routes.auth import require_shop_user, get_current_shop_id
from src.models.shop import Shop
from src.models.customer import Customer
from src.models.product import Product
from src.models.invoice import Invoice
from src.models.payment import InvoicePayment


shop_bp = Blueprint('shop', __name__)

@shop_bp.route('/dashboard', methods=['GET'])
@require_shop_user
def get_shop_dashboard():
    """Get shop dashboard statistics"""
    try:
        shop_id = get_current_shop_id()
        if not shop_id:
            return jsonify({'error': 'Shop not found'}), 404
        
        shop = Shop.get_by_id(shop_id)
        if not shop:
            return jsonify({'error': 'Shop not found'}), 404
        
        stats = shop.get_dashboard_stats()
        
        # Get recent invoices
        recent_invoices = Invoice.get_by_shop_id(shop_id, limit=5)
        
        # Get low stock products
        low_stock_products = Product.get_low_stock_products(shop_id)
        
        return jsonify({
            'shop': shop.to_dict(),
            'stats': stats,
            'recent_invoices': [invoice.to_dict(include_customer=True) for invoice in recent_invoices],
            'low_stock_products': [product.to_dict() for product in low_stock_products[:5]]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@shop_bp.route('/profile', methods=['GET'])
@require_shop_user
def get_shop_profile():
    """Get shop profile"""
    try:
        shop_id = get_current_shop_id()
        if not shop_id:
            return jsonify({'error': 'Shop not found'}), 404
        
        shop = Shop.get_by_id(shop_id)
        if not shop:
            return jsonify({'error': 'Shop not found'}), 404
        
        return jsonify({'shop': shop.to_dict()}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@shop_bp.route('/profile', methods=['PUT'])
@require_shop_user
def update_shop_profile():
    """Update shop profile"""
    try:
        shop_id = get_current_shop_id()
        if not shop_id:
            return jsonify({'error': 'Shop not found'}), 404
        
        shop = Shop.get_by_id(shop_id)
        if not shop:
            return jsonify({'error': 'Shop not found'}), 404
        
        data = request.get_json()
        
        # Update shop
        if shop.update(**data):
            return jsonify({
                'message': 'Shop profile updated successfully',
                'shop': shop.to_dict()
            }), 200
        else:
            return jsonify({'error': 'Failed to update shop profile'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Customer routes
@shop_bp.route('/customers', methods=['GET'])
@require_shop_user
def get_customers():
    """Get shop customers"""
    try:
        shop_id = get_current_shop_id()
        if not shop_id:
            return jsonify({'error': 'Shop not found'}), 404
        
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))
        search = request.args.get('search')
        
        offset = (page - 1) * limit
        
        customers = Customer.get_by_shop_id(shop_id, limit=limit, offset=offset, search=search)
        
        # Get total count for pagination
        from src.database_sqlite import get_db_connection
        with get_db_connection() as conn:
            cursor = conn.cursor()
            if search:
                cursor.execute('''
                    SELECT COUNT(*) FROM customers 
                    WHERE shop_id = ? AND (name LIKE ? OR phone LIKE ? OR email LIKE ?)
                ''', (shop_id, f'%{search}%', f'%{search}%', f'%{search}%'))
            else:
                cursor.execute('SELECT COUNT(*) FROM customers WHERE shop_id = ?', (shop_id,))
            total_count = cursor.fetchone()[0]
        
        return jsonify({
            'customers': [customer.to_dict() for customer in customers],
            'pagination': {
                'page': page,
                'limit': limit,
                'total': total_count,
                'pages': (total_count + limit - 1) // limit
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@shop_bp.route('/customers', methods=['POST'])
@require_shop_user
def create_customer():
    """Create new customer"""
    try:
        shop_id = get_current_shop_id()
        if not shop_id:
            return jsonify({'error': 'Shop not found'}), 404
        
        data = request.get_json()
        
        # Validate required fields
        if not data.get('name'):
            return jsonify({'error': 'Customer name is required'}), 400
        
        customer = Customer.create(shop_id, data)
        
        return jsonify({
            'message': 'Customer created successfully',
            'customer': customer.to_dict()
        }), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@shop_bp.route('/customers/<int:customer_id>', methods=['PUT'])
@require_shop_user
def update_customer(customer_id):
    """Update customer"""
    try:
        shop_id = get_current_shop_id()
        if not shop_id:
            return jsonify({'error': 'Shop not found'}), 404
        
        customer = Customer.get_by_id(customer_id)
        if not customer or customer.shop_id != shop_id:
            return jsonify({'error': 'Customer not found'}), 404
        
        data = request.get_json()
        
        if customer.update(**data):
            return jsonify({
                'message': 'Customer updated successfully',
                'customer': customer.to_dict()
            }), 200
        else:
            return jsonify({'error': 'Failed to update customer'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@shop_bp.route('/customers/<int:customer_id>', methods=['DELETE'])
@require_shop_user
def delete_customer(customer_id):
    """Delete customer"""
    try:
        shop_id = get_current_shop_id()
        if not shop_id:
            return jsonify({'error': 'Shop not found'}), 404
        
        customer = Customer.get_by_id(customer_id)
        if not customer or customer.shop_id != shop_id:
            return jsonify({'error': 'Customer not found'}), 404
        
        if customer.delete():
            return jsonify({'message': 'Customer deleted successfully'}), 200
        else:
            return jsonify({'error': 'Failed to delete customer'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@shop_bp.route('/customers/<int:customer_id>', methods=['GET'])
@require_shop_user
def get_customer_details(customer_id):
    """Get customer details with invoice history"""
    try:
        shop_id = get_current_shop_id()
        if not shop_id:
            return jsonify({'error': 'Shop not found'}), 404
        
        customer = Customer.get_by_id(customer_id)
        if not customer or customer.shop_id != shop_id:
            return jsonify({'error': 'Customer not found'}), 404
        
        # Get customer's invoices with payment details
        invoices = Invoice.get_by_customer_id(customer_id, shop_id)
        
        # Calculate customer summary
        total_invoices = len(invoices)
        total_amount = sum(invoice.total_amount for invoice in invoices)
        total_paid = sum(invoice.paid_amount for invoice in invoices)
        total_due = total_amount - total_paid
        overdue_amount = sum(invoice.balance_amount for invoice in invoices if invoice.status == 'overdue')
        
        # Get recent payments
        recent_payments = customer.get_recent_payments(limit=10)
        
        customer_summary = {
            'total_invoices': total_invoices,
            'total_amount': total_amount,
            'total_paid': total_paid,
            'total_due': total_due,
            'overdue_amount': overdue_amount,
            'payment_history': recent_payments
        }
        
        return jsonify({
            'customer': customer.to_dict(),
            'invoices': [invoice.to_dict(include_items=True, include_payments=True) for invoice in invoices],
            'summary': customer_summary
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Product routes
@shop_bp.route('/products', methods=['GET'])
@require_shop_user
def get_products():
    """Get shop products"""
    try:
        shop_id = get_current_shop_id()
        if not shop_id:
            return jsonify({'error': 'Shop not found'}), 404
        
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))
        search = request.args.get('search')
        category = request.args.get('category')
        
        offset = (page - 1) * limit
        
        products = Product.get_by_shop_id(
            shop_id, limit=limit, offset=offset, 
            search=search, category=category
        )
        
        # Get total count for pagination
        from src.database_sqlite import get_db_connection
        with get_db_connection() as conn:
            cursor = conn.cursor()
            query = 'SELECT COUNT(*) FROM products WHERE shop_id = ? AND is_active = 1'
            params = [shop_id]
            
            if search:
                query += ' AND (name LIKE ? OR brand LIKE ? OR barcode LIKE ?)'
                params.extend([f'%{search}%', f'%{search}%', f'%{search}%'])
            
            if category:
                query += ' AND category = ?'
                params.append(category)
            
            cursor.execute(query, params)
            total_count = cursor.fetchone()[0]
        
        return jsonify({
            'products': [product.to_dict() for product in products],
            'pagination': {
                'page': page,
                'limit': limit,
                'total': total_count,
                'pages': (total_count + limit - 1) // limit
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@shop_bp.route('/products', methods=['POST'])
@require_shop_user
def create_product():
    """Create new product"""
    try:
        shop_id = get_current_shop_id()
        if not shop_id:
            return jsonify({'error': 'Shop not found'}), 404
        
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'category', 'unit', 'price']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400
        
        product = Product.create(shop_id, data)
        
        return jsonify({
            'message': 'Product created successfully',
            'product': product.to_dict()
        }), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@shop_bp.route('/products/<int:product_id>', methods=['PUT'])
@require_shop_user
def update_product(product_id):
    """Update product"""
    try:
        shop_id = get_current_shop_id()
        if not shop_id:
            return jsonify({'error': 'Shop not found'}), 404
        
        product = Product.get_by_id(product_id)
        if not product or product.shop_id != shop_id:
            return jsonify({'error': 'Product not found'}), 404
        
        data = request.get_json()
        
        if product.update(**data):
            return jsonify({
                'message': 'Product updated successfully',
                'product': product.to_dict()
            }), 200
        else:
            return jsonify({'error': 'Failed to update product'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@shop_bp.route('/products/categories', methods=['GET'])
@require_shop_user
def get_product_categories():
    """Get product categories"""
    try:
        shop_id = get_current_shop_id()
        if not shop_id:
            return jsonify({'error': 'Shop not found'}), 404
        
        categories = Product.get_categories(shop_id)
        
        return jsonify({'categories': categories}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Invoice routes
@shop_bp.route('/invoices', methods=['GET'])
@require_shop_user
def get_invoices():
    """Get shop invoices"""
    try:
        shop_id = get_current_shop_id()
        if not shop_id:
            return jsonify({'error': 'Shop not found'}), 404
        
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))
        status = request.args.get('status')
        search = request.args.get('search')
        sort = request.args.get('sort', 'latest')
        date_filter = request.args.get('date')
        
        offset = (page - 1) * limit
        
        invoices = Invoice.get_by_shop_id(
            shop_id, limit=limit, offset=offset, 
            status=status, search=search, sort=sort, date_filter=date_filter
        )
        
        # Get total count for pagination
        from src.database_sqlite import get_db_connection
        with get_db_connection() as conn:
            cursor = conn.cursor()
            query = '''
                SELECT COUNT(*) FROM invoices i
                LEFT JOIN customers c ON i.customer_id = c.id
                WHERE i.shop_id = ?
            '''
            params = [shop_id]
            
            if status:
                query += ' AND i.status = ?'
                params.append(status)
            
            if search:
                query += ' AND (i.invoice_number LIKE ? OR c.name LIKE ?)'
                params.extend([f'%{search}%', f'%{search}%'])
            
            if date_filter:
                query += ' AND DATE(i.invoice_date) = ?'
                params.append(date_filter)
            
            cursor.execute(query, params)
            total_count = cursor.fetchone()[0]
        
        return jsonify({
            'invoices': [invoice.to_dict(include_customer=True) for invoice in invoices],
            'pagination': {
                'page': page,
                'limit': limit,
                'total': total_count,
                'pages': (total_count + limit - 1) // limit
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@shop_bp.route('/invoices', methods=['POST'])
@require_shop_user
def create_invoice():
    """Create new invoice with optional immediate payment"""
    try:
        shop_id = get_current_shop_id()
        if not shop_id:
            return jsonify({'error': 'Shop not found'}), 404
        
        data = request.get_json()
        
        # Validate required fields
        if not data.get('invoice_date'):
            return jsonify({'error': 'Invoice date is required'}), 400
        
        if not data.get('items') or len(data['items']) == 0:
            return jsonify({'error': 'Invoice items are required'}), 400
        
        # Validate items
        for item in data['items']:
            if not all(key in item for key in ['product_id', 'quantity', 'unit_price']):
                return jsonify({'error': 'Invalid item data'}), 400
        
        # Create invoice
        invoice = Invoice.create(shop_id, data, data['items'])
        
        # Handle immediate payment if provided
        immediate_payment = data.get('immediate_payment', {})
        if immediate_payment and immediate_payment.get('amount', 0) > 0:
            payment_amount = float(immediate_payment['amount'])
            if payment_amount > invoice.total_amount:
                return jsonify({'error': 'Payment amount cannot exceed invoice total'}), 400
            
            # Add immediate payment
            invoice.add_payment(
                amount=payment_amount,
                payment_method=immediate_payment.get('payment_method', 'cash'),
                payment_date=immediate_payment.get('payment_date', data['invoice_date']),
                reference_number=immediate_payment.get('reference_number', ''),
                notes=immediate_payment.get('notes', '')
            )
        
        return jsonify({
            'message': 'Invoice created successfully',
            'invoice': invoice.to_dict(include_items=True, include_customer=True, include_payments=True)
        }), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@shop_bp.route('/invoices/<int:invoice_id>', methods=['GET'])
@require_shop_user
def get_invoice(invoice_id):
    """Get invoice details"""
    try:
        shop_id = get_current_shop_id()
        if not shop_id:
            return jsonify({'error': 'Shop not found'}), 404
        
        invoice = Invoice.get_by_id(invoice_id)
        if not invoice or invoice.shop_id != shop_id:
            return jsonify({'error': 'Invoice not found'}), 404
        
        return jsonify({
            'invoice': invoice.to_dict(include_items=True, include_customer=True)
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@shop_bp.route('/invoices/<int:invoice_id>', methods=['DELETE'])
@require_shop_user
def delete_invoice(invoice_id):
    """Delete invoice"""
    try:
        shop_id = get_current_shop_id()
        if not shop_id:
            return jsonify({'error': 'Shop not found'}), 404
        
        invoice = Invoice.get_by_id(invoice_id)
        if not invoice or invoice.shop_id != shop_id:
            return jsonify({'error': 'Invoice not found'}), 404
        
        if invoice.delete():
            return jsonify({'message': 'Invoice deleted successfully'}), 200
        else:
            return jsonify({'error': 'Failed to delete invoice'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@shop_bp.route('/invoices/<int:invoice_id>/payments', methods=['POST'])
@require_shop_user
def add_payment_to_invoice(invoice_id):
    """Add payment to invoice"""
    try:
        shop_id = get_current_shop_id()
        if not shop_id:
            return jsonify({'error': 'Shop not found'}), 404
        
        invoice = Invoice.get_by_id(invoice_id)
        if not invoice or invoice.shop_id != shop_id:
            return jsonify({'error': 'Invoice not found'}), 404
        
        data = request.get_json()
        
        # Validate required fields
        if not data.get('amount') or not data.get('payment_method'):
            return jsonify({'error': 'Amount and payment method are required'}), 400
        
        if data['amount'] <= 0:
            return jsonify({'error': 'Payment amount must be positive'}), 400
        
        if data['amount'] > invoice.balance_amount:
            return jsonify({'error': 'Payment amount cannot exceed balance amount'}), 400
        
        # Add payment
        if invoice.add_payment(
            amount=data['amount'],
            payment_method=data['payment_method'],
            payment_date=data.get('payment_date'),
            reference_number=data.get('reference_number'),
            notes=data.get('notes')
        ):
                    return jsonify({
            'message': 'Payment added successfully',
            'invoice': invoice.to_dict(include_items=True, include_customer=True, include_payments=True)
        }), 200
        else:
            return jsonify({'error': 'Failed to add payment'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@shop_bp.route('/invoices/<int:invoice_id>/payments', methods=['GET'])
@require_shop_user
def get_invoice_payments(invoice_id):
    """Get payment history for invoice"""
    try:
        shop_id = get_current_shop_id()
        if not shop_id:
            return jsonify({'error': 'Shop not found'}), 404
        
        invoice = Invoice.get_by_id(invoice_id)
        if not invoice or invoice.shop_id != shop_id:
            return jsonify({'error': 'Invoice not found'}), 404
        
        payments = invoice.get_payments()
        payment_summary = invoice.get_payment_summary()
        
        return jsonify({
            'payments': [payment.to_dict() for payment in payments],
            'payment_summary': payment_summary,
            'invoice': invoice.to_dict(include_items=True, include_customer=True)
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@shop_bp.route('/invoices/<int:invoice_id>/return', methods=['POST'])
@require_shop_user
def process_invoice_return(invoice_id):
    """Process return for invoice items"""
    try:
        shop_id = get_current_shop_id()
        if not shop_id:
            return jsonify({'error': 'Shop not found'}), 404
        
        invoice = Invoice.get_by_id(invoice_id)
        if not invoice or invoice.shop_id != shop_id:
            return jsonify({'error': 'Invoice not found'}), 404
        
        data = request.get_json()
        
        # Validate required fields
        if not data.get('return_items') or len(data['return_items']) == 0:
            return jsonify({'error': 'Return items are required'}), 400
        
        # Validate return items
        for item in data['return_items']:
            if not all(key in item for key in ['invoice_item_id', 'returned_quantity']):
                return jsonify({'error': 'Invalid return item data'}), 400
            
            if item['returned_quantity'] <= 0:
                return jsonify({'error': 'Returned quantity must be positive'}), 400
        
        # Process return
        return_amount = invoice.process_return(data['return_items'])
        
        # Get updated invoice
        updated_invoice = Invoice.get_by_id(invoice_id)
        
        return jsonify({
            'message': 'Return processed successfully',
            'return_amount': return_amount,
            'invoice': updated_invoice.to_dict(include_items=True, include_customer=True)
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Expense routes
@shop_bp.route('/expenses', methods=['GET'])
@require_shop_user
def get_expenses():
    """Get shop expenses"""
    try:
        shop_id = get_current_shop_id()
        if not shop_id:
            return jsonify({'error': 'Shop not found'}), 404
        
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))
        category = request.args.get('category')
        search = request.args.get('search')
        sort = request.args.get('sort', 'latest')
        date_filter = request.args.get('date')
        
        offset = (page - 1) * limit
        
        from src.models.expense import Expense
        expenses = Expense.get_by_shop_id(
            shop_id, limit=limit, offset=offset, 
            category=category, search=search, sort=sort, date_filter=date_filter
        )
        
        # Get total count for pagination
        from src.database_sqlite import get_db_connection
        with get_db_connection() as conn:
            cursor = conn.cursor()
            query = 'SELECT COUNT(*) FROM expenses WHERE shop_id = ?'
            params = [shop_id]
            
            if category:
                query += ' AND category = ?'
                params.append(category)
            
            if search:
                query += ' AND (title LIKE ? OR description LIKE ?)'
                params.extend([f'%{search}%', f'%{search}%'])
            
            if date_filter:
                query += ' AND DATE(expense_date) = ?'
                params.append(date_filter)
            
            cursor.execute(query, params)
            total_count = cursor.fetchone()[0]
        
        return jsonify({
            'expenses': [expense.to_dict() for expense in expenses],
            'pagination': {
                'page': page,
                'limit': limit,
                'total': total_count,
                'pages': (total_count + limit - 1) // limit
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@shop_bp.route('/expenses', methods=['POST'])
@require_shop_user
def create_expense():
    """Create new expense"""
    try:
        shop_id = get_current_shop_id()
        if not shop_id:
            return jsonify({'error': 'Shop not found'}), 404
        
        data = request.get_json()
        
        # Validate required fields
        if not data.get('title'):
            return jsonify({'error': 'Expense title is required'}), 400
        
        if not data.get('amount') or data['amount'] <= 0:
            return jsonify({'error': 'Valid expense amount is required'}), 400
        
        if not data.get('category'):
            return jsonify({'error': 'Expense category is required'}), 400
        
        if not data.get('expense_date'):
            return jsonify({'error': 'Expense date is required'}), 400
        
        # Create expense
        from src.models.expense import Expense
        expense = Expense.create(shop_id, data)
        
        return jsonify({
            'message': 'Expense created successfully',
            'expense': expense.to_dict()
        }), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@shop_bp.route('/expenses/<int:expense_id>', methods=['GET'])
@require_shop_user
def get_expense(expense_id):
    """Get expense by ID"""
    try:
        shop_id = get_current_shop_id()
        if not shop_id:
            return jsonify({'error': 'Shop not found'}), 404
        
        from src.models.expense import Expense
        expense = Expense.get_by_id(expense_id)
        if not expense or expense.shop_id != shop_id:
            return jsonify({'error': 'Expense not found'}), 404
        
        return jsonify({
            'expense': expense.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@shop_bp.route('/expenses/<int:expense_id>', methods=['DELETE'])
@require_shop_user
def delete_expense(expense_id):
    """Delete expense"""
    try:
        shop_id = get_current_shop_id()
        if not shop_id:
            return jsonify({'error': 'Shop not found'}), 404
        
        from src.models.expense import Expense
        expense = Expense.get_by_id(expense_id)
        if not expense or expense.shop_id != shop_id:
            return jsonify({'error': 'Expense not found'}), 404
        
        expense.delete()
        
        return jsonify({
            'message': 'Expense deleted successfully'
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500