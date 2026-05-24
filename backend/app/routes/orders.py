from flask import Blueprint, jsonify, request
from app import db
from app.models import Order, Customer, Inventory, Product
from datetime import datetime

orders_bp = Blueprint('orders', __name__)


@orders_bp.route('/')
def list_orders():
    """Paginated orders list with search and filter."""
    page     = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    status   = request.args.get('status', '')
    search   = request.args.get('search', '')
    date_from = request.args.get('date_from', '')
    date_to   = request.args.get('date_to', '')

    query = Order.query

    if status:
        query = query.filter(Order.status == status)
    if search:
        query = query.join(Customer).filter(
            db.or_(
                Customer.name.ilike(f'%{search}%'),
                Customer.email.ilike(f'%{search}%'),
                Order.order_number.ilike(f'%{search}%')
            )
        )
    if date_from:
        query = query.filter(Order.created_at >= datetime.fromisoformat(date_from))
    if date_to:
        query = query.filter(Order.created_at <= datetime.fromisoformat(date_to))

    query = query.order_by(Order.created_at.desc())
    paginated = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        'orders': [o.to_dict() for o in paginated.items],
        'total': paginated.total,
        'pages': paginated.pages,
        'current_page': page,
    })


@orders_bp.route('/<int:order_id>')
def get_order(order_id):
    """Single order with full item detail."""
    order = Order.query.get_or_404(order_id)
    return jsonify(order.to_dict(include_items=True))


@orders_bp.route('/<int:order_id>/status', methods=['PUT'])
def update_status(order_id):
    """Update order status."""
    order = Order.query.get_or_404(order_id)
    data  = request.get_json()
    new_status = data.get('status')

    if new_status not in Order.STATUS_CHOICES:
        return jsonify({'error': f'Invalid status. Must be one of: {Order.STATUS_CHOICES}'}), 400

    order.status = new_status
    order.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify(order.to_dict())


@orders_bp.route('/stats')
def order_stats():
    """Quick order count by status."""
    from sqlalchemy import func
    results = db.session.query(Order.status, func.count(Order.id)).group_by(Order.status).all()
    return jsonify({r[0]: r[1] for r in results})
