from flask import Blueprint, jsonify, request
from app import db
from app.models import Order, OrderItem, Product, Inventory
from sqlalchemy import func, text
from datetime import datetime, timedelta

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/kpis')
def get_kpis():
    """Main KPI cards for dashboard."""
    now = datetime.utcnow()
    month_start = now.replace(day=1, hour=0, minute=0, second=0)
    prev_month_start = (month_start - timedelta(days=1)).replace(day=1)

    # This month
    orders_this_month = Order.query.filter(
        Order.created_at >= month_start,
        Order.status != 'Cancelled'
    ).all()

    # Previous month
    orders_prev_month = Order.query.filter(
        Order.created_at >= prev_month_start,
        Order.created_at < month_start,
        Order.status != 'Cancelled'
    ).all()

    revenue_this  = sum(o.total_amount for o in orders_this_month)
    revenue_prev  = sum(o.total_amount for o in orders_prev_month)
    profit_this   = sum(o.profit for o in orders_this_month)
    profit_prev   = sum(o.profit for o in orders_prev_month)

    def pct_change(current, previous):
        if previous == 0:
            return 100 if current > 0 else 0
        return round(((current - previous) / previous) * 100, 1)

    # Low stock count
    low_stock = Inventory.query.filter(
        Inventory.quantity <= Inventory.reorder_point,
        Inventory.quantity > 0
    ).count()
    out_of_stock = Inventory.query.filter(Inventory.quantity == 0).count()

    return jsonify({
        'total_orders': {
            'value': len(orders_this_month),
            'change': pct_change(len(orders_this_month), len(orders_prev_month)),
            'label': 'vs last month'
        },
        'revenue': {
            'value': round(revenue_this, 2),
            'change': pct_change(revenue_this, revenue_prev),
            'label': 'vs last month'
        },
        'profit': {
            'value': round(profit_this, 2),
            'change': pct_change(profit_this, profit_prev),
            'label': 'vs last month'
        },
        'low_stock_alerts': {
            'value': low_stock,
            'out_of_stock': out_of_stock,
            'label': 'products need restock'
        },
    })


@dashboard_bp.route('/sales-trend')
def get_sales_trend():
    """Daily sales trend for chart. period: 7d, 30d, 90d"""
    period = request.args.get('period', '30d')
    days = {'7d': 7, '30d': 30, '90d': 90}.get(period, 30)
    start_date = datetime.utcnow() - timedelta(days=days)

    # Group by date
    results = db.session.query(
        func.date(Order.created_at).label('date'),
        func.sum(Order.total_amount).label('revenue'),
        func.count(Order.id).label('orders')
    ).filter(
        Order.created_at >= start_date,
        Order.status != 'Cancelled'
    ).group_by(func.date(Order.created_at)).order_by('date').all()

    data = [{'date': str(r.date), 'revenue': round(float(r.revenue or 0), 2), 'orders': r.orders}
            for r in results]
    return jsonify(data)


@dashboard_bp.route('/top-products')
def get_top_products():
    """Top 10 best-selling products by revenue."""
    results = db.session.query(
        Product.id,
        Product.name,
        Product.sku,
        func.sum(OrderItem.quantity).label('units_sold'),
        func.sum(OrderItem.quantity * OrderItem.unit_price).label('revenue')
    ).join(OrderItem, Product.id == OrderItem.product_id
    ).join(Order, OrderItem.order_id == Order.id
    ).filter(Order.status != 'Cancelled'
    ).group_by(Product.id
    ).order_by(db.desc('revenue')).limit(10).all()

    return jsonify([{
        'id': r.id, 'name': r.name, 'sku': r.sku,
        'units_sold': int(r.units_sold or 0),
        'revenue': round(float(r.revenue or 0), 2)
    } for r in results])


@dashboard_bp.route('/order-status-distribution')
def get_order_status():
    """Order count by status for pie chart."""
    results = db.session.query(
        Order.status,
        func.count(Order.id).label('count')
    ).group_by(Order.status).all()
    return jsonify([{'status': r.status, 'count': r.count} for r in results])


@dashboard_bp.route('/recent-orders')
def get_recent_orders():
    """Last 10 orders for dashboard table."""
    orders = Order.query.order_by(Order.created_at.desc()).limit(10).all()
    return jsonify([o.to_dict() for o in orders])


@dashboard_bp.route('/inventory-alerts')
def get_inventory_alerts():
    """Products below reorder point."""
    low = db.session.query(Product, Inventory).join(
        Inventory, Product.id == Inventory.product_id
    ).filter(Inventory.quantity <= Inventory.reorder_point).order_by(Inventory.quantity).limit(8).all()

    return jsonify([{
        **p.to_dict(include_inventory=False),
        'inventory': inv.to_dict()
    } for p, inv in low])
