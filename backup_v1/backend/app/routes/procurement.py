from flask import Blueprint, jsonify, request
from app import db
from app.models import Supplier, ProcurementRequest, Product, Inventory
from datetime import datetime, timedelta

procurement_bp = Blueprint('procurement', __name__)


# ─── Suppliers ────────────────────────────────────────────────────────────────

@procurement_bp.route('/suppliers')
def list_suppliers():
    suppliers = Supplier.query.filter_by(is_active=True).order_by(Supplier.name).all()
    return jsonify([s.to_dict() for s in suppliers])


@procurement_bp.route('/suppliers/<int:supplier_id>')
def get_supplier(supplier_id):
    s = Supplier.query.get_or_404(supplier_id)
    data = s.to_dict()
    data['recent_requests'] = [
        r.to_dict() for r in s.procurement_requests.order_by(
            ProcurementRequest.requested_at.desc()
        ).limit(10).all()
    ]
    return jsonify(data)


# ─── Procurement Requests ─────────────────────────────────────────────────────

@procurement_bp.route('/requests')
def list_requests():
    status = request.args.get('status', '')
    query  = ProcurementRequest.query
    if status:
        query = query.filter(ProcurementRequest.status == status)
    reqs = query.order_by(ProcurementRequest.requested_at.desc()).all()
    return jsonify([r.to_dict() for r in reqs])


@procurement_bp.route('/requests', methods=['POST'])
def create_request():
    data = request.get_json()
    pr = ProcurementRequest(
        supplier_id   = data['supplier_id'],
        product_id    = data['product_id'],
        quantity      = data['quantity'],
        unit_cost     = data.get('unit_cost'),
        total_cost    = data.get('unit_cost', 0) * data['quantity'],
        notes         = data.get('notes', ''),
        expected_at   = datetime.utcnow() + timedelta(days=data.get('lead_time_days', 7))
    )
    db.session.add(pr)
    db.session.commit()
    return jsonify(pr.to_dict()), 201


@procurement_bp.route('/requests/<int:req_id>/status', methods=['PUT'])
def update_request_status(req_id):
    pr   = ProcurementRequest.query.get_or_404(req_id)
    data = request.get_json()
    new_status = data.get('status')
    if new_status not in ProcurementRequest.STATUS_CHOICES:
        return jsonify({'error': 'Invalid status'}), 400
    pr.status = new_status
    if new_status == 'Received':
        pr.received_at = datetime.utcnow()
        # Auto-update inventory
        inv = Inventory.query.filter_by(product_id=pr.product_id).first()
        if inv:
            inv.quantity += pr.quantity
            inv.last_restocked = datetime.utcnow()
    db.session.commit()
    return jsonify(pr.to_dict())


# ─── Auto Reorder Suggestions (Analytics-driven) ─────────────────────────────

@procurement_bp.route('/suggestions')
def get_reorder_suggestions():
    """
    Products below reorder point → suggest procurement.
    NOTE: When real analytics/forecasting runs, this will also factor in
    demand forecast to calculate smarter reorder quantities.
    """
    from sqlalchemy import func
    low_stock = db.session.query(Product, Inventory).join(
        Inventory, Product.id == Inventory.product_id
    ).filter(Inventory.quantity <= Inventory.reorder_point).all()

    suggestions = []
    for product, inv in low_stock:
        # Find preferred supplier (last used or highest rated)
        last_req = ProcurementRequest.query.filter_by(
            product_id=product.id, status='Received'
        ).order_by(ProcurementRequest.requested_at.desc()).first()

        suggestions.append({
            'product_id': product.id,
            'product_name': product.name,
            'product_sku': product.sku,
            'current_stock': inv.quantity,
            'reorder_point': inv.reorder_point,
            'suggested_quantity': inv.reorder_quantity,
            'estimated_cost': round(product.cost * inv.reorder_quantity, 2),
            'last_supplier_id': last_req.supplier_id if last_req else None,
            'last_supplier_name': last_req.supplier.name if last_req else None,
            'urgency': 'Critical' if inv.quantity == 0 else 'High',
        })

    return jsonify(sorted(suggestions, key=lambda x: x['current_stock']))
