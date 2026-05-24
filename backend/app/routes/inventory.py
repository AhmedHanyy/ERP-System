from flask import Blueprint, jsonify, request
from app import db
from app.models import Inventory, Product, Category, InventoryLog
from datetime import datetime

inventory_bp = Blueprint('inventory', __name__)


@inventory_bp.route('/')
def list_inventory():
    """Product inventory list with filters."""
    category  = request.args.get('category', '')
    status    = request.args.get('status', '')
    search    = request.args.get('search', '')
    page      = request.args.get('page', 1, type=int)
    per_page  = request.args.get('per_page', 20, type=int)

    query = db.session.query(Product, Inventory).join(
        Inventory, Product.id == Inventory.product_id
    )

    if category:
        query = query.filter(Product.category_id == int(category))
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
def adjust_inventory(product_id):
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
    db.session.commit()

    return jsonify({'inventory': inv.to_dict(), 'log': log.to_dict()})


@inventory_bp.route('/summary')
def inventory_summary():
    """Quick summary stats."""
    total    = Inventory.query.count()
    low      = Inventory.query.filter(Inventory.quantity <= Inventory.reorder_point, Inventory.quantity > 0).count()
    out      = Inventory.query.filter(Inventory.quantity == 0).count()
    in_stock = total - low - out
    return jsonify({'total': total, 'in_stock': in_stock, 'low_stock': low, 'out_of_stock': out})
