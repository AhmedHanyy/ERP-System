from flask import Blueprint, jsonify, request
from app import db
from app.models import Supplier, ProcurementRequest, Product, Inventory, AuditLog, InventoryLog
from sqlalchemy import func
from datetime import datetime, timedelta
from .auth import token_required, roles_required

procurement_bp = Blueprint('procurement', __name__)


def compute_supplier_performance_fast(supplier_id):
    """
    Compute supplier KPIs using SQL aggregation — NO ORM iteration over 17k rows.
    """
    received = db.session.query(
        func.count(ProcurementRequest.id).label('cnt'),
        func.avg(
            func.julianday(ProcurementRequest.received_at) -
            func.julianday(ProcurementRequest.requested_at)
        ).label('avg_lead')
    ).filter(
        ProcurementRequest.supplier_id == supplier_id,
        ProcurementRequest.status == 'Received',
        ProcurementRequest.received_at.isnot(None),
        ProcurementRequest.requested_at.isnot(None)
    ).first()

    cancelled = db.session.query(
        func.count(ProcurementRequest.id)
    ).filter(
        ProcurementRequest.supplier_id == supplier_id,
        ProcurementRequest.status == 'Cancelled'
    ).scalar() or 0

    s = Supplier.query.get(supplier_id)
    received_cnt  = received.cnt or 0
    avg_lead_days = float(received.avg_lead or s.lead_time_days or 7)
    total_closed  = received_cnt + cancelled

    if avg_lead_days > (s.lead_time_days or 7):
        lead_time_score = max(50.0, min(100.0, 100.0 - (avg_lead_days - s.lead_time_days) * 8.0))
    else:
        lead_time_score = 100.0

    reliability_score = (received_cnt / total_closed * 100.0) if total_closed > 0 else 100.0
    cost_score = 95.0
    overall_score = 0.4 * reliability_score + 0.3 * lead_time_score + 0.3 * cost_score

    return {
        'lead_time_score': round(lead_time_score, 1),
        'reliability_score': round(reliability_score, 1),
        'cost_score': round(cost_score, 1),
        'overall_score': round(overall_score, 1),
        'avg_actual_lead_days': round(avg_lead_days, 1),
        'is_demo': not s.is_real
    }


# ─── Suppliers ────────────────────────────────────────────────────────────────

@procurement_bp.route('/suppliers')
@roles_required('Admin', 'Procurement Staff', 'Procurement Officer', 'Operations Manager')
def list_suppliers(current_user):
    suppliers = Supplier.query.filter_by(is_active=True).all()
    res = []
    for s in suppliers:
        s_dict = s.to_dict()
        perf = compute_supplier_performance_fast(s.id)
        s_dict.update(perf)
        res.append(s_dict)
    res = sorted(res, key=lambda x: x['overall_score'], reverse=True)
    for i, s_dict in enumerate(res):
        s_dict['rank'] = i + 1
    return jsonify(res)


@procurement_bp.route('/suppliers/<int:supplier_id>')
@roles_required('Admin', 'Procurement Staff', 'Procurement Officer', 'Operations Manager')
def get_supplier(current_user, supplier_id):
    s = Supplier.query.get_or_404(supplier_id)
    data = s.to_dict()
    perf = compute_supplier_performance_fast(s.id)
    data.update(perf)
    data['rank'] = 1  # Only 2 suppliers, rank is simple

    # Last 10 requests for this supplier (most recent first)
    data['recent_requests'] = [
        r.to_dict() for r in ProcurementRequest.query.filter_by(
            supplier_id=supplier_id
        ).order_by(
            ProcurementRequest.requested_at.desc()
        ).limit(10).all()
    ]
    return jsonify(data)


# ─── Procurement Requests — PAGINATED ─────────────────────────────────────────

@procurement_bp.route('/requests')
@roles_required('Admin', 'Procurement Staff', 'Procurement Officer', 'Operations Manager')
def list_requests(current_user):
    """
    Paginated procurement requests — returns max 50 per page.
    Filters: status, supplier_id, product_id, is_real
    """
    page        = request.args.get('page', 1, type=int)
    per_page    = min(request.args.get('per_page', 20, type=int), 100)  # cap at 100
    status      = request.args.get('status', '')
    supplier_id = request.args.get('supplier_id', '', type=str)
    is_real     = request.args.get('is_real', None)

    query = ProcurementRequest.query

    if status:
        status_list = [s.strip() for s in status.split(',') if s.strip()]
        if len(status_list) > 1:
            query = query.filter(ProcurementRequest.status.in_(status_list))
        elif len(status_list) == 1:
            query = query.filter(ProcurementRequest.status == status_list[0])
    if supplier_id:
        query = query.filter(ProcurementRequest.supplier_id == int(supplier_id))
    if is_real is not None:
        flag = is_real.lower() == 'true'
        query = query.filter(ProcurementRequest.is_real == flag)

    query = query.order_by(ProcurementRequest.requested_at.desc())
    paginated = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        'requests': [r.to_dict() for r in paginated.items],
        'total': paginated.total,
        'pages': paginated.pages,
        'current_page': page,
    })


@procurement_bp.route('/requests', methods=['POST'])
@roles_required('Admin', 'Procurement Staff', 'Procurement Officer')
def create_request(current_user):
    data = request.get_json()
    product = Product.query.get(data['product_id'])

    # Determine supplier by business rule if not provided:
    # Printed products → Feathers (id=1), Non-printed → Printlet (id=2)
    supplier_id = data.get('supplier_id')
    if not supplier_id and product:
        name_lower = (product.name or '').lower()
        desc_lower = (product.description or '').lower()
        is_printed = 'printed' in name_lower or 'graphic' in name_lower or 'printed' in desc_lower
        supplier_id = 1 if is_printed else 2

    unit_cost = data.get('unit_cost') or (product.cost if product else 0)
    quantity  = int(data.get('quantity', 50))
    pr = ProcurementRequest(
        supplier_id   = supplier_id,
        product_id    = data['product_id'],
        quantity      = quantity,
        unit_cost     = unit_cost,
        total_cost    = round(unit_cost * quantity, 2),
        notes         = data.get('notes', ''),
        status        = 'Draft',
        is_real       = True,
        is_auto_suggested = data.get('is_auto_suggested', False),
        expected_at   = datetime.utcnow() + timedelta(days=data.get('lead_time_days', 7))
    )
    db.session.add(pr)
    db.session.commit()

    log = AuditLog(
        user_id=current_user.id,
        action=f"Created Procurement Request PO #{pr.id}",
        target_table="procurement_requests",
        target_id=pr.id,
        new_value=str(pr.to_dict())
    )
    db.session.add(log)
    db.session.commit()

    return jsonify(pr.to_dict()), 201


@procurement_bp.route('/requests/<int:req_id>/status', methods=['PUT'])
@roles_required('Admin', 'Procurement Staff', 'Procurement Officer')
def update_request_status(current_user, req_id):
    pr   = ProcurementRequest.query.get_or_404(req_id)
    data = request.get_json()
    new_status = data.get('status')
    if new_status not in ProcurementRequest.STATUS_CHOICES:
        return jsonify({'error': 'Invalid status'}), 400

    old_status = pr.status
    pr.status  = new_status

    if new_status == 'Received':
        pr.received_at = datetime.utcnow()
        inv = Inventory.query.filter_by(product_id=pr.product_id).first()
        if inv:
            inv.quantity += pr.quantity
            inv.last_restocked = datetime.utcnow()
            db.session.add(InventoryLog(
                product_id=pr.product_id, change=pr.quantity,
                reason=f"PO #{pr.id} Restock"
            ))
            db.session.add(AuditLog(
                user_id=current_user.id,
                action=f"Restocked via PO #{pr.id}",
                target_table="inventory",
                target_id=inv.id,
                old_value=str(inv.quantity - pr.quantity),
                new_value=str(inv.quantity)
            ))

    db.session.commit()
    db.session.add(AuditLog(
        user_id=current_user.id,
        action=f"Updated PO #{pr.id} status",
        target_table="procurement_requests",
        target_id=pr.id,
        old_value=old_status,
        new_value=new_status
    ))
    db.session.commit()
    return jsonify(pr.to_dict())


# ─── Summary Stats ────────────────────────────────────────────────────────────

@procurement_bp.route('/stats')
@token_required
def procurement_stats(current_user):
    """Quick summary stats for dashboard — does NOT load all rows."""
    stats = db.session.query(
        ProcurementRequest.status,
        func.count(ProcurementRequest.id).label('count'),
        func.sum(ProcurementRequest.total_cost).label('total_cost')
    ).group_by(ProcurementRequest.status).all()

    return jsonify([{
        'status': r.status,
        'count': r.count,
        'total_cost': round(float(r.total_cost or 0), 2)
    } for r in stats])


# ─── Auto Reorder Suggestions ─────────────────────────────────────────────────

@procurement_bp.route('/suggestions')
@roles_required('Admin', 'Procurement Staff', 'Procurement Officer', 'Operations Manager')
def get_reorder_suggestions(current_user):
    """Products below reorder point with suggested order quantities."""
    low_stock = db.session.query(Product, Inventory).join(
        Inventory, Product.id == Inventory.product_id
    ).filter(Inventory.quantity <= Inventory.reorder_point).all()

    # Business rule: is_printed → supplier Feathers (1), else Printlet (2)
    def get_supplier_id(product):
        name = (product.name or '').lower()
        desc = (product.description or '').lower()
        return 1 if ('printed' in name or 'graphic' in name or 'printed' in desc) else 2

    # Last received PO per product (aggregated)
    last_pos = db.session.query(
        ProcurementRequest.product_id,
        func.max(ProcurementRequest.requested_at).label('last_date'),
        ProcurementRequest.supplier_id
    ).filter(ProcurementRequest.status == 'Received').group_by(
        ProcurementRequest.product_id
    ).all()
    last_po_map = {r.product_id: r for r in last_pos}

    suggestions = []
    for product, inv in low_stock:
        last_po = last_po_map.get(product.id)
        sugg_supplier_id = get_supplier_id(product)
        supplier = Supplier.query.get(sugg_supplier_id)

        suggestions.append({
            'product_id': product.id,
            'product_name': product.name,
            'product_sku': product.sku,
            'current_stock': inv.quantity,
            'reorder_point': inv.reorder_point,
            'suggested_quantity': inv.reorder_quantity,
            'estimated_cost': round(product.cost * inv.reorder_quantity, 2),
            'supplier_id': sugg_supplier_id,
            'supplier_name': supplier.name if supplier else 'Unknown',
            'urgency': 'Critical' if inv.quantity == 0 else 'High',
        })

    return jsonify(sorted(suggestions, key=lambda x: x['current_stock']))
