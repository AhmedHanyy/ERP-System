from flask import Blueprint, jsonify, request
from app import db
from app.models import Customer, Order, OrderItem, Product
from sqlalchemy import func
from .auth import token_required, roles_required

customers_bp = Blueprint('customers', __name__)


@customers_bp.route('/')
@roles_required('Admin', 'Customer Service')
def list_customers(current_user):
    """
    Paginated customers list with aggregated metrics.
    Excludes the Unknown fallback customer.
    Uses SQL aggregation — no N+1 queries.
    """
    page     = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    segment  = request.args.get('segment', '')
    search   = request.args.get('search', '')

    # Aggregation subquery: order count + lifetime value per customer
    order_stats = db.session.query(
        Order.customer_id.label('cid'),
        func.count(Order.id).label('order_count'),
        func.sum(Order.total_amount).label('ltv'),
        func.min(Order.created_at).label('first_order'),
        func.max(Order.created_at).label('last_order'),
    ).filter(Order.status != 'Cancelled').group_by(Order.customer_id).subquery()

    # Select Customer model + aggregated columns explicitly
    query = db.session.query(
        Customer,
        order_stats.c.order_count,
        order_stats.c.ltv,
        order_stats.c.first_order,
        order_stats.c.last_order,
    ).outerjoin(
        order_stats, Customer.id == order_stats.c.cid
    ).filter(
        Customer.email != 'unknown@leveld.store'
    )

    if segment:
        query = query.filter(Customer.segment == segment)
    if search:
        query = query.filter(
            db.or_(
                Customer.name.ilike(f'%{search}%'),
                Customer.email.ilike(f'%{search}%'),
                Customer.city.ilike(f'%{search}%'),
            )
        )

    # Count for pagination
    total = query.count()

    # Sort by lifetime value desc (best customers first)
    rows = query.order_by(
        db.desc(order_stats.c.ltv),
        Customer.created_at.desc()
    ).offset((page - 1) * per_page).limit(per_page).all()

    customers = []
    for row in rows:
        cust         = row[0]
        order_count  = row[1]
        ltv          = row[2]
        first_order  = row[3]
        last_order   = row[4]
        d = {
            'id': cust.id,
            'name': cust.name,
            'email': cust.email,
            'phone': cust.phone,
            'address': cust.address,
            'city': cust.city,
            'country': cust.country,
            'segment': cust.segment,
            'rfm_score': cust.rfm_score,
            'created_at': cust.created_at.isoformat(),
            'total_orders': int(order_count or 0),
            'lifetime_value': round(float(ltv or 0), 2),
            'avg_order_value': round(float(ltv or 0) / max(int(order_count or 0), 1), 2),
            'first_order_date': first_order.isoformat() if first_order else None,
            'last_order_date': last_order.isoformat() if last_order else None,
        }
        customers.append(d)

    return jsonify({
        'customers': customers,
        'total': total,
        'pages': -(-total // per_page),   # ceiling division
        'current_page': page,
    })


@customers_bp.route('/<int:customer_id>')
@roles_required('Admin', 'Customer Service')
def get_customer(current_user, customer_id):
    """Customer detail with order history and computed metrics."""
    c = Customer.query.get_or_404(customer_id)

    # Get order stats via SQL (not Python iteration)
    stats = db.session.query(
        func.count(Order.id).label('order_count'),
        func.sum(Order.total_amount).label('ltv'),
        func.min(Order.created_at).label('first_order'),
        func.max(Order.created_at).label('last_order'),
    ).filter(Order.customer_id == c.id, Order.status != 'Cancelled').first()

    data = {
        'id': c.id,
        'name': c.name,
        'email': c.email,
        'phone': c.phone,
        'address': c.address,
        'city': c.city,
        'country': c.country,
        'segment': c.segment,
        'rfm_score': c.rfm_score,
        'created_at': c.created_at.isoformat(),
        'total_orders': int(stats.order_count or 0),
        'lifetime_value': round(float(stats.ltv or 0), 2),
        'avg_order_value': round(float(stats.ltv or 0) / max(int(stats.order_count or 0), 1), 2),
        'first_order_date': stats.first_order.isoformat() if stats.first_order else None,
        'last_order_date': stats.last_order.isoformat() if stats.last_order else None,
    }

    # Recent orders (last 20)
    recent_orders = c.orders.filter(Order.status != 'Cancelled').order_by(
        Order.created_at.desc()
    ).limit(20).all()
    data['orders'] = [o.to_dict(include_items=True) for o in recent_orders]

    # Product purchase history (distinct products bought)
    products_bought = db.session.query(
        Product.id, Product.name, Product.sku,
        func.sum(OrderItem.quantity).label('total_qty'),
        func.count(func.distinct(Order.id)).label('order_count_prod'),
    ).join(OrderItem, Product.id == OrderItem.product_id).join(
        Order, OrderItem.order_id == Order.id
    ).filter(
        Order.customer_id == c.id,
        Order.status != 'Cancelled'
    ).group_by(Product.id, Product.name, Product.sku).order_by(
        db.desc('total_qty')
    ).all()

    data['purchased_products'] = [{
        'product_id': r[0],
        'product_name': r[1],
        'product_sku': r[2],
        'total_qty': int(r[3] or 0),
        'order_count': int(r[4] or 0),
    } for r in products_bought]

    return jsonify(data)


@customers_bp.route('/segments')
@token_required
def segment_summary(current_user):
    results = db.session.query(
        Customer.segment, func.count(Customer.id)
    ).filter(
        Customer.email != 'unknown@leveld.store'
    ).group_by(Customer.segment).all()
    return jsonify([{'segment': r[0] or 'Unknown', 'count': r[1]} for r in results])


@customers_bp.route('/top')
@token_required
def top_customers(current_user):
    """Top 10 customers by lifetime value (for dashboard widget)."""
    stats = db.session.query(
        Customer.id, Customer.name, Customer.email, Customer.city, Customer.segment,
        func.count(Order.id).label('order_count'),
        func.sum(Order.total_amount).label('ltv'),
    ).join(Order, Order.customer_id == Customer.id).filter(
        Customer.email != 'unknown@leveld.store',
        Order.status != 'Cancelled'
    ).group_by(Customer.id).order_by(db.desc('ltv')).limit(10).all()

    return jsonify([{
        'id': r[0], 'name': r[1], 'email': r[2], 'city': r[3], 'segment': r[4],
        'total_orders': int(r[5] or 0),
        'lifetime_value': round(float(r[6] or 0), 2),
    } for r in stats])
