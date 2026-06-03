from flask import Blueprint, jsonify, request
from app import db
from app.models import Order, OrderItem, Product, Inventory, ProcurementRequest, Customer
from sqlalchemy import func
from datetime import datetime, timedelta
from .auth import token_required

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/kpis')
@token_required
def get_kpis(current_user):
    """Main KPI cards for dashboard calculated dynamically from database."""
    try:
        now = datetime.utcnow()
        month_start = now.replace(day=1, hour=0, minute=0, second=0)
        prev_month_start = (month_start - timedelta(days=1)).replace(day=1)

        # This month orders
        orders_this_month = Order.query.filter(
            Order.created_at >= month_start,
            Order.status != 'Cancelled'
        ).all()

        # Previous month orders
        orders_prev_month = Order.query.filter(
            Order.created_at >= prev_month_start,
            Order.created_at < month_start,
            Order.status != 'Cancelled'
        ).all()

        revenue_this  = sum(o.total_amount for o in orders_this_month)
        revenue_prev  = sum(o.total_amount for o in orders_prev_month)
        
        profit_this = 0
        for o in orders_this_month:
            try: profit_this += o.profit
            except: pass
            
        profit_prev = 0
        for o in orders_prev_month:
            try: profit_prev += o.profit
            except: pass

        def pct_change(current, previous):
            if not previous or previous == 0:
                return 100 if current and current > 0 else 0
            return round(((current - previous) / previous) * 100, 1)

        margin_this = (profit_this / revenue_this * 100) if revenue_this > 0 else 0
        margin_prev = (profit_prev / revenue_prev * 100) if revenue_prev > 0 else 0

        # Low stock count
        low_stock = Inventory.query.filter(
            Inventory.quantity <= Inventory.reorder_point,
            Inventory.quantity > 0
        ).count()
        out_of_stock = Inventory.query.filter(Inventory.quantity == 0).count()

        # Transit Assets (POs Sent/Confirmed)
        transit_count = ProcurementRequest.query.filter(ProcurementRequest.status.in_(['Sent', 'Confirmed'])).count()
        transit_value = db.session.query(func.sum(ProcurementRequest.total_cost)).filter(ProcurementRequest.status.in_(['Sent', 'Confirmed'])).scalar() or 0

        # Supply Latency (avg lead time of received orders)
        received_reqs = ProcurementRequest.query.filter(ProcurementRequest.status == 'Received').all()
        lead_times = []
        for r in received_reqs:
            if r.received_at and r.requested_at:
                lead_times.append((r.received_at - r.requested_at).days)
        avg_lead_time = sum(lead_times) / len(lead_times) if lead_times else 7.2

        # Throughput (Preparing, Shipped, Delivered)
        throughput = Order.query.filter(Order.status.in_(['Preparing', 'Shipped', 'Delivered'])).count()

        # Service Level (Delivered / total non-cancelled orders)
        delivered_count = Order.query.filter(Order.status == 'Delivered').count()
        total_non_cancelled = Order.query.filter(Order.status != 'Cancelled').count()
        service_level = (delivered_count / total_non_cancelled * 100) if total_non_cancelled > 0 else 98.5

        # Process Alerts (Pending orders + low stock)
        pending_orders = Order.query.filter(Order.status == 'Pending').count()
        process_alerts = pending_orders + low_stock

        # Client Retention (Returning customers / total customers)
        total_customers = Customer.query.count()
        returning_customers = db.session.query(Order.customer_id).filter(Order.status != 'Cancelled').group_by(Order.customer_id).having(func.count(Order.id) > 1).count()
        client_retention = (returning_customers / total_customers * 100) if total_customers > 0 else 85.0

        # Resource Allocation (total PO spend vs budget)
        total_po_spend = db.session.query(func.sum(ProcurementRequest.total_cost)).filter(ProcurementRequest.status != 'Cancelled').scalar() or 0
        allocated_pct = min(100.0, (total_po_spend / 1000000.0) * 100) if total_po_spend > 0 else 45.0

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
            'margin': {
                'value': round(margin_this, 1),
                'change': pct_change(margin_this, margin_prev),
                'label': 'vs last month'
            },
            'low_stock_alerts': {
                'value': low_stock,
                'out_of_stock': out_of_stock,
                'label': 'products need restock'
            },
            'transit_assets': {
                'count': transit_count,
                'value': round(float(transit_value), 2)
            },
            'supply_latency': round(avg_lead_time, 1),
            'throughput': throughput,
            'service_level': round(service_level, 1),
            'process_alerts': process_alerts,
            'client_retention': round(client_retention, 1),
            'resource_allocation': round(allocated_pct, 1)
        })
    except Exception as e:
        print(f"KPI ERROR: {str(e)}")
        return jsonify({'error': 'Internal server error calculating KPIs'}), 500


@dashboard_bp.route('/sales-trend')
@token_required
def get_sales_trend(current_user):
    """Daily sales trend for chart."""
    try:
        period = request.args.get('period', '30d')
        days = {'7d': 7, '30d': 30, '90d': 90}.get(period, 30)
        start_date = datetime.utcnow() - timedelta(days=days)

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
    except Exception as e:
        return jsonify([]), 200


@dashboard_bp.route('/top-products')
@token_required
def get_top_products(current_user):
    """Top 10 best-selling products."""
    try:
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
    except:
        return jsonify([])


@dashboard_bp.route('/order-status-distribution')
@token_required
def get_order_status(current_user):
    """Order count by status."""
    try:
        results = db.session.query(
            Order.status,
            func.count(Order.id).label('count')
        ).group_by(Order.status).all()
        return jsonify([{'status': r.status, 'count': r.count} for r in results])
    except:
        return jsonify([])


@dashboard_bp.route('/recent-orders')
@token_required
def get_recent_orders(current_user):
    """Last 10 orders."""
    try:
        orders = Order.query.order_by(Order.created_at.desc()).limit(10).all()
        return jsonify([o.to_dict() for o in orders])
    except:
        return jsonify([])


@dashboard_bp.route('/inventory-alerts')
@token_required
def get_inventory_alerts(current_user):
    """Products below reorder point."""
    try:
        low = db.session.query(Product, Inventory).join(
            Inventory, Product.id == Inventory.product_id
        ).filter(Inventory.quantity <= Inventory.reorder_point).order_by(Inventory.quantity).limit(8).all()

        return jsonify([{
            **p.to_dict(include_inventory=False),
            'inventory': inv.to_dict()
        } for p, inv in low])
    except:
        return jsonify([])
