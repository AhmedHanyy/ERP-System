from flask import Blueprint, jsonify, request
from app import db
from app.models.warehouse import FactSales, DimProduct, DimCustomer, FactInventory, FactProcurement, DimSupplier, DimDate
from sqlalchemy import func
from datetime import datetime, timedelta
from .auth import token_required

dashboard_bp = Blueprint('dashboard', __name__)

def filter_kpis_by_role(kpis_dict, role):
    if role in ('Procurement Officer', 'Procurement Staff'):
        allowed = {'low_stock_alerts', 'transit_assets', 'supply_latency', 'resource_allocation'}
        return {k: v for k, v in kpis_dict.items() if k in allowed}
    elif role == 'Customer Service':
        allowed = {'total_orders', 'client_retention', 'service_level', 'throughput'}
        return {k: v for k, v in kpis_dict.items() if k in allowed}
    return kpis_dict


@dashboard_bp.route('/kpis')
@token_required
def get_kpis(current_user):
    """
    Main KPI cards — operational DB for all-time counts (correct),
    warehouse for revenue/profit aggregates (IsSynthetic=False only).
    Products = parent product count (264), NOT dim_product variant rows (2342).
    """
    try:
        from app.models import Order, Customer, Product, Inventory as Inv
        from sqlalchemy import func as sfunc

        def pct_change(current, previous):
            if not previous or previous == 0:
                return 100.0 if (current and current > 0) else 0.0
            return round(((current - previous) / previous) * 100, 1)

        # ── PERIOD ANCHOR: use max real DateKey so we never show empty months ──
        max_dk = db.session.query(func.max(FactSales.DateKey)).filter(
            FactSales.IsSynthetic == False
        ).scalar()
        if max_dk:
            s = str(max_dk)
            now = datetime(int(s[:4]), int(s[4:6]), int(s[6:]))
        else:
            now = datetime.utcnow()
        month_start    = now.replace(day=1, hour=0, minute=0, second=0)
        prev_mon_start = (month_start - timedelta(days=1)).replace(day=1)
        month_start_key = int(month_start.strftime('%Y%m%d'))
        prev_mon_key    = int(prev_mon_start.strftime('%Y%m%d'))

        # ── TOTAL REVENUE (all-time, from operational orders) ─────────────────
        rev_total    = db.session.query(sfunc.sum(Order.total_amount)).filter(Order.status != 'Cancelled').scalar() or 0.0
        rev_this_mon = db.session.query(sfunc.sum(Order.total_amount)).filter(Order.status != 'Cancelled', Order.created_at >= month_start).scalar() or 0.0
        rev_prev_mon = db.session.query(sfunc.sum(Order.total_amount)).filter(Order.status != 'Cancelled', Order.created_at >= prev_mon_start, Order.created_at < month_start).scalar() or 0.0

        # ── TOTAL ORDERS ──────────────────────────────────────────────────────
        orders_total    = db.session.query(sfunc.count(Order.id)).filter(Order.status != 'Cancelled').scalar() or 0
        orders_this_mon = db.session.query(sfunc.count(Order.id)).filter(Order.status != 'Cancelled', Order.created_at >= month_start).scalar() or 0
        orders_prev_mon = db.session.query(sfunc.count(Order.id)).filter(Order.status != 'Cancelled', Order.created_at >= prev_mon_start, Order.created_at < month_start).scalar() or 0

        # ── TOTAL CUSTOMERS (exclude fallback) ───────────────────────────────
        total_customers = db.session.query(sfunc.count(Customer.id)).filter(Customer.email != 'unknown@leveld.store').scalar() or 0
        cust_this_mon   = db.session.query(sfunc.count(Customer.id)).filter(Customer.email != 'unknown@leveld.store', Customer.created_at >= month_start).scalar() or 0
        cust_prev_mon   = db.session.query(sfunc.count(Customer.id)).filter(Customer.email != 'unknown@leveld.store', Customer.created_at >= prev_mon_start, Customer.created_at < month_start).scalar() or 0

        # ── ACTIVE PRODUCTS (is_active=True products, 126 active / 264 total) ──
        total_products = db.session.query(sfunc.count(Product.id)).filter(Product.is_active == True).scalar() or 0

        # ── INVENTORY VALUE ───────────────────────────────────────────────────
        inventory_value = db.session.query(
            sfunc.sum(Inv.quantity * Product.cost)
        ).join(Product, Inv.product_id == Product.id).scalar() or 0.0

        # ── PROFIT & MARGIN from warehouse (real only) ────────────────────────
        def wh_kpis(extra_filter=None):
            filters = [FactSales.IsSynthetic == False, FactSales.IsCancelled == False]
            if extra_filter is not None:
                filters.append(extra_filter)
            rev_q  = db.session.query(func.sum(FactSales.GrossRevenue - FactSales.DiscountAmount)).filter(*filters).scalar() or 0.0
            cogs_q = db.session.query(func.sum(FactSales.UnitCost * FactSales.Quantity)).filter(*filters).scalar() or 0.0
            sq = db.session.query(FactSales.OrderNumber, func.max(FactSales.OrderShipping).label('s')).filter(*filters).group_by(FactSales.OrderNumber).subquery()
            ship_q = db.session.query(func.sum(sq.c.s)).scalar() or 0.0
            tot_rev  = rev_q + ship_q
            gprofit  = tot_rev - cogs_q
            gmargin  = (gprofit / tot_rev * 100) if tot_rev > 0 else 0.0
            return tot_rev, gprofit, gmargin

        _, gprofit_all, gmargin_all = wh_kpis()
        _, gprofit_this, gmargin_this = wh_kpis(FactSales.DateKey >= month_start_key)
        _, gprofit_prev, gmargin_prev = wh_kpis(
            (FactSales.DateKey >= prev_mon_key) & (FactSales.DateKey < month_start_key)
        )

        # ── AOV ───────────────────────────────────────────────────────────────
        aov_total = float(rev_total) / orders_total if orders_total > 0 else 0.0
        aov_this  = float(rev_this_mon) / orders_this_mon if orders_this_mon > 0 else 0.0
        aov_prev  = float(rev_prev_mon) / orders_prev_mon if orders_prev_mon > 0 else 0.0

        # ── INVENTORY ALERTS ──────────────────────────────────────────────────
        low_stock    = Inv.query.filter(Inv.quantity > 0, Inv.quantity <= Inv.reorder_point).count()
        out_of_stock = Inv.query.filter(Inv.quantity == 0).count()

        # ── OPERATIONS ────────────────────────────────────────────────────────
        transit_count = FactProcurement.query.filter(FactProcurement.Status.in_(['Sent', 'Confirmed'])).count()
        transit_value = db.session.query(func.sum(FactProcurement.TotalCost)).filter(FactProcurement.Status.in_(['Sent', 'Confirmed'])).scalar() or 0.0
        avg_lead      = db.session.query(func.avg(FactProcurement.LeadTimeDays)).filter(FactProcurement.Status == 'Received').scalar() or 7.0

        delivered     = db.session.query(sfunc.count(Order.id)).filter(Order.status == 'Delivered').scalar() or 0
        service_level = (delivered / orders_total * 100) if orders_total > 0 else 0.0

        returning = db.session.query(Order.customer_id).filter(Order.status != 'Cancelled').group_by(Order.customer_id).having(sfunc.count(Order.id) > 1).count()
        client_retention = (returning / total_customers * 100) if total_customers > 0 else 0.0

        pending_orders = db.session.query(sfunc.count(Order.id)).filter(Order.status == 'Pending').scalar() or 0
        process_alerts = pending_orders + low_stock

        res_dict = {
            'revenue':        {'value': round(float(rev_total), 2),      'period_value': round(float(rev_this_mon), 2),   'change': pct_change(rev_this_mon, rev_prev_mon),      'label': 'all-time revenue'},
            'orders':         {'value': orders_total,                     'period_value': orders_this_mon,                  'change': pct_change(orders_this_mon, orders_prev_mon), 'label': 'all-time orders'},
            'customers':      {'value': total_customers,                  'period_value': cust_this_mon,                    'change': pct_change(cust_this_mon, cust_prev_mon),     'label': 'total customers'},
            'products':       {'value': total_products,                   'change': 0.0,                                    'label': 'active products'},
            'inventory_value':{'value': round(float(inventory_value), 2), 'change': 0.0,                                    'label': 'warehouse value'},
            'aov':            {'value': round(aov_total, 2),              'period_value': round(aov_this, 2),               'change': pct_change(aov_this, aov_prev),               'label': 'avg order value'},
            'gross_profit':   {'value': round(float(gprofit_all), 2),     'period_value': round(float(gprofit_this), 2),    'change': pct_change(gprofit_this, gprofit_prev),       'label': 'all-time gross profit'},
            'gross_margin':   {'value': round(float(gmargin_all), 1),     'period_value': round(float(gmargin_this), 1),    'change': pct_change(gmargin_this, gmargin_prev),       'label': 'gross margin %'},
            'total_orders':   {'value': orders_total,   'change': pct_change(orders_this_mon, orders_prev_mon), 'label': 'all-time orders'},
            'margin':         {'value': round(float(gmargin_all), 1), 'change': pct_change(gmargin_this, gmargin_prev), 'label': 'gross margin %'},
            'low_stock_alerts':{'value': low_stock, 'out_of_stock': out_of_stock, 'label': 'products need restock'},
            'transit_assets': {'count': transit_count, 'value': round(float(transit_value), 2)},
            'supply_latency': round(float(avg_lead), 1),
            'throughput':     delivered,
            'service_level':  round(float(service_level), 1),
            'process_alerts': process_alerts,
            'client_retention': round(float(client_retention), 1),
            'resource_allocation': round(min(100.0, (float(transit_value) / 100000.0) * 100), 1)
        }
        return jsonify(filter_kpis_by_role(res_dict, current_user.role))
    except Exception as e:
        import traceback
        print(f"KPI ERROR: {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500


@dashboard_bp.route('/sales-trend')
@token_required
def get_sales_trend(current_user):
    """Daily sales trend for chart from database warehouse."""
    try:
        period = request.args.get('period', '30d')
        days = {'7d': 7, '30d': 30, '90d': 90}.get(period, 30)

        max_datekey = db.session.query(func.max(FactSales.DateKey)).filter(FactSales.IsSynthetic == False).scalar()
        if max_datekey:
            str_dk = str(max_datekey)
            now = datetime(int(str_dk[:4]), int(str_dk[4:6]), int(str_dk[6:]))
        else:
            now = datetime.utcnow()
        start_date = now - timedelta(days=days)

        results = db.session.query(
            DimDate.FullDate.label('date'),
            func.sum(FactSales.GrossRevenue - FactSales.DiscountAmount).label('revenue'),
            func.count(func.distinct(FactSales.OrderNumber)).label('orders')
        ).join(
            DimDate, FactSales.DateKey == DimDate.DateKey
        ).filter(
            FactSales.IsSynthetic == False,
            FactSales.IsCancelled == False,
            DimDate.FullDate >= start_date.date()
        ).group_by(DimDate.FullDate).order_by('date').all()

        data = [{'date': str(r.date), 'revenue': round(float(r.revenue or 0), 2), 'orders': r.orders}
                for r in results]
        return jsonify(data)
    except Exception as e:
        print(f"Sales Trend error: {e}")
        return jsonify([]), 200


@dashboard_bp.route('/top-products')
@token_required
def get_top_products(current_user):
    """Top 10 best-selling products from database warehouse (real sales only)."""
    try:
        results = db.session.query(
            DimProduct.ProductKey.label('id'),
            DimProduct.Title.label('name'),
            DimProduct.SKU.label('sku'),
            func.sum(FactSales.Quantity).label('units_sold'),
            func.sum(FactSales.GrossRevenue - FactSales.DiscountAmount).label('revenue')
        ).join(
            DimProduct, FactSales.ProductKey == DimProduct.ProductKey
        ).filter(
            FactSales.IsSynthetic == False,
            FactSales.IsCancelled == False,
            DimProduct.IsCurrent == True
        ).group_by(
            DimProduct.ProductKey, DimProduct.Title, DimProduct.SKU
        ).order_by(
            db.desc('revenue')
        ).limit(10).all()

        return jsonify([{
            'id': r.id, 'name': r.name, 'sku': r.sku,
            'units_sold': int(r.units_sold or 0),
            'revenue': round(float(r.revenue or 0), 2)
        } for r in results])
    except Exception as e:
        print(f"Top products error: {e}")
        return jsonify([])


@dashboard_bp.route('/order-status-distribution')
@token_required
def get_order_status(current_user):
    """Order count by status from operational DB."""
    try:
        from app.models import Order
        from sqlalchemy import func as sfunc
        results = db.session.query(Order.status, sfunc.count(Order.id)).group_by(Order.status).all()
        return jsonify([{'status': r[0], 'count': r[1]} for r in results])
    except Exception as e:
        print(f"Status distribution error: {e}")
        return jsonify([])


@dashboard_bp.route('/recent-orders')
@token_required
def get_recent_orders(current_user):
    """Last 10 orders from operational DB with calculated subtotals."""
    try:
        from app.models import Order, Customer, OrderItem, Product
        from sqlalchemy import func as sfunc

        orders = db.session.query(Order).filter(
            Order.status != 'Cancelled'
        ).order_by(Order.created_at.desc()).limit(10).all()

        result = []
        for o in orders:
            cust = Customer.query.get(o.customer_id)
            # Calculate actual subtotal from order items
            subtotal = db.session.query(sfunc.sum(OrderItem.quantity * OrderItem.unit_price)).filter(
                OrderItem.order_id == o.id
            ).scalar() or 0.0

            # Calculate profit from items
            items_with_cost = db.session.query(
                OrderItem.quantity, OrderItem.unit_price, Product.cost
            ).join(Product, OrderItem.product_id == Product.id).filter(
                OrderItem.order_id == o.id
            ).all()
            cogs = sum(qty * cost for qty, price, cost in items_with_cost)
            profit = float(o.total_amount) - cogs

            result.append({
                'id': o.id,
                'order_number': o.order_number,
                'customer_id': o.customer_id,
                'customer_name': cust.name if cust else 'Unknown',
                'customer_email': cust.email if cust else '',
                'status': o.status,
                'total_amount': round(float(o.total_amount), 2),
                'subtotal': round(float(subtotal), 2),
                'profit': round(profit, 2),
                'discount': round(float(o.discount or 0), 2),
                'shipping_fee': round(float(o.shipping_fee or 0), 2),
                'notes': o.notes,
                'created_at': o.created_at.isoformat() if o.created_at else None,
                'updated_at': o.updated_at.isoformat() if o.updated_at else None,
            })
        return jsonify(result)
    except Exception as e:
        import traceback
        print(f"Recent orders error: {traceback.format_exc()}")
        return jsonify([])


@dashboard_bp.route('/inventory-alerts')
@token_required
def get_inventory_alerts(current_user):
    """Products below reorder point from operational inventory."""
    try:
        from app.models import Inventory as Inv, Product
        low = db.session.query(Inv, Product).join(
            Product, Inv.product_id == Product.id
        ).filter(
            Inv.quantity <= Inv.reorder_point
        ).order_by(Inv.quantity).limit(8).all()

        res = []
        for inv, p in low:
            res.append({
                'id': p.id,
                'name': p.name,
                'sku': p.sku,
                'inventory': {
                    'status': inv.status,
                    'quantity': inv.quantity,
                    'reorder_point': inv.reorder_point,
                    'reorder_quantity': inv.reorder_quantity
                }
            })
        return jsonify(res)
    except Exception as e:
        print(f"Inventory alerts error: {e}")
        return jsonify([])
