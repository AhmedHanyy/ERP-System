from flask import Blueprint, jsonify, request
from app import db
from app.models import Supplier, ProcurementRequest, Product, Inventory, AuditLog, InventoryLog
from datetime import datetime, timedelta
from .auth import token_required, roles_required

procurement_bp = Blueprint('procurement', __name__)


def compute_supplier_performance(s):
    if not s.is_real:
        return {
            'lead_time_score': None,
            'reliability_score': None,
            'cost_score': None,
            'overall_score': 0.0,
            'is_demo': True
        }
        
    # Query received orders for this supplier (real only)
    received = ProcurementRequest.query.filter_by(supplier_id=s.id, status='Received', is_real=True).all()
    cancelled = ProcurementRequest.query.filter_by(supplier_id=s.id, status='Cancelled', is_real=True).all()
    
    # 1. Lead Time Score
    if received:
        actual_days_list = []
        for r in received:
            if r.received_at and r.requested_at:
                actual_days = (r.received_at - r.requested_at).days
                actual_days_list.append(actual_days)
        if actual_days_list:
            avg_actual = sum(actual_days_list) / len(actual_days_list)
        else:
            avg_actual = s.lead_time_days
            
        if avg_actual > s.lead_time_days:
            lead_time_score = max(50.0, min(100.0, 100.0 - (avg_actual - s.lead_time_days) * 8.0))
        else:
            lead_time_score = 100.0
    else:
        lead_time_score = 100.0
        
    # 2. Reliability Score: % of non-cancelled out of closed orders
    total_closed = len(received) + len(cancelled)
    if total_closed > 0:
        reliability_score = (len(received) / total_closed) * 100.0
    else:
        reliability_score = 100.0
        
    # 3. Cost Score
    cost_score = 100.0
    
    # 4. Overall Supplier Score
    overall_score = 0.4 * reliability_score + 0.3 * lead_time_score + 0.3 * cost_score
    
    return {
        'lead_time_score': round(lead_time_score, 1),
        'reliability_score': round(reliability_score, 1),
        'cost_score': round(cost_score, 1),
        'overall_score': round(overall_score, 1),
        'is_demo': False
    }


# ─── Suppliers ────────────────────────────────────────────────────────────────

@procurement_bp.route('/suppliers')
@roles_required('Admin', 'Procurement Staff', 'Procurement Officer', 'Operations Manager')
def list_suppliers(current_user):
    suppliers = Supplier.query.filter_by(is_active=True).all()
    res = []
    for s in suppliers:
        s_dict = s.to_dict()
        perf = compute_supplier_performance(s)
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
    perf = compute_supplier_performance(s)
    data.update(perf)
    
    all_suppliers = Supplier.query.filter_by(is_active=True).all()
    ranked = []
    for other in all_suppliers:
        other_perf = compute_supplier_performance(other)
        ranked.append((other.id, other_perf['overall_score']))
    ranked = sorted(ranked, key=lambda x: x[1], reverse=True)
    rank = next((i + 1 for i, item in enumerate(ranked) if item[0] == s.id), None)
    data['rank'] = rank
    
    data['recent_requests'] = [
        r.to_dict() for r in s.procurement_requests.order_by(
            ProcurementRequest.requested_at.desc()
        ).limit(10).all()
    ]
    return jsonify(data)


# ─── Procurement Requests ─────────────────────────────────────────────────────

@procurement_bp.route('/requests')
@roles_required('Admin', 'Procurement Staff', 'Procurement Officer', 'Operations Manager')
def list_requests(current_user):
    status = request.args.get('status', '')
    query  = ProcurementRequest.query
    if status:
        query = query.filter(ProcurementRequest.status == status)
    reqs = query.order_by(ProcurementRequest.requested_at.desc()).all()
    return jsonify([r.to_dict() for r in reqs])


@procurement_bp.route('/requests', methods=['POST'])
@roles_required('Admin', 'Procurement Staff', 'Procurement Officer')
def create_request(current_user):
    data = request.get_json()
    pr = ProcurementRequest(
        supplier_id   = data['supplier_id'],
        product_id    = data['product_id'],
        quantity      = data['quantity'],
        unit_cost     = data.get('unit_cost'),
        total_cost    = data.get('unit_cost', 0) * data['quantity'],
        notes         = data.get('notes', ''),
        status        = 'Draft',
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
    pr.status = new_status
    
    if new_status == 'Received':
        pr.received_at = datetime.utcnow()
        inv = Inventory.query.filter_by(product_id=pr.product_id).first()
        if inv:
            inv.quantity += pr.quantity
            inv.last_restocked = datetime.utcnow()
            
            # Log the adjustment
            log_inv = InventoryLog(product_id=pr.product_id, change=pr.quantity, reason=f"PO #{pr.id} Restock")
            db.session.add(log_inv)
            
            # Audit log for inventory
            log_audit = AuditLog(
                user_id=current_user.id,
                action=f"Restocked inventory via PO #{pr.id} for {pr.product.name if pr.product else 'Product ID ' + str(pr.product_id)}",
                target_table="inventory",
                target_id=inv.id,
                old_value=str(inv.quantity - pr.quantity),
                new_value=str(inv.quantity)
            )
            db.session.add(log_audit)
            
    db.session.commit()
    
    # Audit log for PO status change
    log = AuditLog(
        user_id=current_user.id,
        action=f"Updated Procurement Request PO #{pr.id} status",
        target_table="procurement_requests",
        target_id=pr.id,
        old_value=old_status,
        new_value=new_status
    )
    db.session.add(log)
    db.session.commit()
    
    return jsonify(pr.to_dict())


# ─── Auto Reorder Suggestions (Analytics-driven) ─────────────────────────────

@procurement_bp.route('/suggestions')
@roles_required('Admin', 'Procurement Staff', 'Procurement Officer', 'Operations Manager')
def get_reorder_suggestions(current_user):
    """
    Products below reorder point → suggest procurement.
    """
    low_stock = db.session.query(Product, Inventory).join(
        Inventory, Product.id == Inventory.product_id
    ).filter(Inventory.quantity <= Inventory.reorder_point).all()

    suggestions = []
    for product, inv in low_stock:
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
