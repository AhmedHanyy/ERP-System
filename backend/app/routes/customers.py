from flask import Blueprint, jsonify, request
from app import db
from app.models import Customer, Order

customers_bp = Blueprint('customers', __name__)


@customers_bp.route('/')
def list_customers():
    page     = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    segment  = request.args.get('segment', '')
    search   = request.args.get('search', '')

    query = Customer.query
    if segment:
        query = query.filter(Customer.segment == segment)
    if search:
        query = query.filter(
            db.or_(Customer.name.ilike(f'%{search}%'), Customer.email.ilike(f'%{search}%'))
        )

    query = query.order_by(Customer.created_at.desc())
    paginated = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        'customers': [c.to_dict() for c in paginated.items],
        'total': paginated.total,
        'pages': paginated.pages,
        'current_page': page,
    })


@customers_bp.route('/<int:customer_id>')
def get_customer(customer_id):
    c = Customer.query.get_or_404(customer_id)
    data = c.to_dict()
    data['orders'] = [o.to_dict(include_items=True) for o in c.orders.order_by(Order.created_at.desc()).limit(20).all()]
    return jsonify(data)


@customers_bp.route('/segments')
def segment_summary():
    from sqlalchemy import func
    results = db.session.query(Customer.segment, func.count(Customer.id)).group_by(Customer.segment).all()
    return jsonify([{'segment': r[0], 'count': r[1]} for r in results])
