from flask import Blueprint, jsonify, request
from app import db
from app.models import Inventory, Product, Category, InventoryLog, AuditLog, ProductVariant
from datetime import datetime
from sqlalchemy import func
from .auth import token_required, roles_required

inventory_bp = Blueprint('inventory', __name__)


@inventory_bp.route('/')
@roles_required('Admin', 'Operations Manager', 'Procurement Staff', 'Procurement Officer')
def list_inventory(current_user):
    """Product inventory list with filters."""
    category    = request.args.get('category', '')
    status      = request.args.get('status', '')
    search      = request.args.get('search', '')
    type_filter = request.args.get('type', '')
    print_style = request.args.get('print_style', '')
    page        = request.args.get('page', 1, type=int)
    per_page    = request.args.get('per_page', 20, type=int)

    query = db.session.query(Product, Inventory).join(
        Inventory, Product.id == Inventory.product_id
    )

    if category:
        query = query.filter(Product.category_id == int(category))
    if type_filter:
        query = query.filter(Product.name.ilike(f'%{type_filter}%'))
    if print_style:
        from app.models.warehouse import DimProduct
        printed_titles_query = db.session.query(DimProduct.Title).filter(
            DimProduct.Graphic != 'Plain',
            DimProduct.Graphic != 'Basic',
            DimProduct.Graphic != None
        ).distinct()
        printed_titles = [r[0] for r in printed_titles_query.all()]
        
        if print_style == 'Printed':
            query = query.filter(Product.name.in_(printed_titles))
        elif print_style == 'Basic':
            query = query.filter(~Product.name.in_(printed_titles))
    if search:
        query = query.filter(Product.name.ilike(f'%{search}%'))
    if status == 'Low Stock':
        query = query.filter(Inventory.quantity <= Inventory.reorder_point, Inventory.quantity > 0)
    elif status == 'Out of Stock':
        query = query.filter(Inventory.quantity == 0)
    elif status == 'In Stock':
        query = query.filter(Inventory.quantity > Inventory.reorder_point)

    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()

    return jsonify({
        'items': [{**p.to_dict(include_inventory=False), 'inventory': inv.to_dict()} for p, inv in items],
        'total': total,
        'pages': (total + per_page - 1) // per_page,
        'current_page': page,
    })


@inventory_bp.route('/<int:product_id>/adjust', methods=['PUT'])
@roles_required('Admin', 'Operations Manager', 'Procurement Staff', 'Procurement Officer')
def adjust_inventory(current_user, product_id):
    """Manual inventory adjustment (in/out/set)."""
    inv = Inventory.query.filter_by(product_id=product_id).first_or_404()
    data = request.get_json()

    adjustment_type = data.get('type', 'add')  # 'add', 'remove', 'set'
    quantity = data.get('quantity', 0)
    reason   = data.get('reason', 'Manual adjustment')

    old_qty = inv.quantity
    if adjustment_type == 'add':
        inv.quantity += quantity
        change = quantity
    elif adjustment_type == 'remove':
        inv.quantity = max(0, inv.quantity - quantity)
        change = -(old_qty - inv.quantity)
    elif adjustment_type == 'set':
        change = quantity - old_qty
        inv.quantity = quantity

    inv.updated_at = datetime.utcnow()
    if change > 0:
        inv.last_restocked = datetime.utcnow()

    # Log the adjustment
    log = InventoryLog(product_id=product_id, change=change, reason=reason)
    db.session.add(log)
    
    # Audit log
    log_audit = AuditLog(
        user_id=current_user.id,
        action=f"Adjusted inventory of {inv.product.name if inv.product else 'Product ID ' + str(product_id)}",
        target_table="inventory",
        target_id=inv.id,
        old_value=str(old_qty),
        new_value=str(inv.quantity)
    )
    db.session.add(log_audit)
    db.session.commit()

    return jsonify({'inventory': inv.to_dict(), 'log': log.to_dict()})


@inventory_bp.route('/summary')
@token_required
def inventory_summary(current_user):
    """Quick summary stats."""
    total_products = Product.query.count()
    total_variants = ProductVariant.query.count()
    low      = Inventory.query.filter(Inventory.quantity <= Inventory.reorder_point, Inventory.quantity > 0).count()
    out      = Inventory.query.filter(Inventory.quantity == 0).count()
    in_stock = total_products - low - out
    
    # Calculate total inventory value
    value = db.session.query(
        func.sum(Inventory.quantity * Product.cost)
    ).join(Product, Inventory.product_id == Product.id).scalar() or 0.0
    
    return jsonify({
        'total': total_products,
        'total_variants': total_variants,
        'in_stock': in_stock,
        'low_stock': low,
        'out_of_stock': out,
        'value': round(value, 2)
    })
