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

        range_param = request.args.get('range', 'all')
        
        # ── PERIOD ANCHOR: use max real DateKey so we never show empty months ──
        max_dk = db.session.query(func.max(FactSales.DateKey)).filter(
            FactSales.IsSynthetic == False
        ).scalar()
        if max_dk:
            s = str(max_dk)
            now = datetime(int(s[:4]), int(s[4:6]), int(s[6:]))
        else:
            now = datetime.utcnow()
            
        # Determine filter boundary based on range param
        if range_param == '30d':
            start_bound = now - timedelta(days=30)
        elif range_param == '90d':
            start_bound = now - timedelta(days=90)
        elif range_param == '6m':
            start_bound = now - timedelta(days=180)
        elif range_param == '12m':
            start_bound = now - timedelta(days=365)
        else:
            start_bound = datetime(2000, 1, 1) # all time
            
        start_bound_key = int(start_bound.strftime('%Y%m%d'))

        month_start    = now.replace(day=1, hour=0, minute=0, second=0)
        prev_mon_start = (month_start - timedelta(days=1)).replace(day=1)
        month_start_key = int(month_start.strftime('%Y%m%d'))
        prev_mon_key    = int(prev_mon_start.strftime('%Y%m%d'))

        # ── KPI AGGREGATION FROM WAREHOUSE ────────────────────────────────────
        # Uses FactSales (IsSynthetic=False, IsCancelled=False).
        # NO ProductKey filter — matches the BI report and operational DB counts.
        # ProductKey=0 items are real Shopify orders for unresolved products;
        # they are included in totals and shown separately as unmapped_stats.
        def get_wh_metrics(time_filter=None):
            filters = [FactSales.IsSynthetic == False, FactSales.IsCancelled == False]
            if time_filter is not None:
                filters.append(time_filter)
            
            # Revenue & COGS
            rev_q  = db.session.query(func.sum(FactSales.GrossRevenue - FactSales.DiscountAmount)).filter(*filters).scalar() or 0.0
            cogs_q = db.session.query(func.sum(FactSales.UnitCost * FactSales.Quantity)).filter(*filters).scalar() or 0.0
            
            # Shipping (deduplicated per order)
            sq = db.session.query(FactSales.OrderNumber, func.max(FactSales.OrderShipping).label('s')).filter(*filters).group_by(FactSales.OrderNumber).subquery()
            ship_q = db.session.query(func.sum(sq.c.s)).scalar() or 0.0
            
            # Counts
            orders_q = db.session.query(func.count(FactSales.OrderNumber.distinct())).filter(*filters).scalar() or 0
            custs_q  = db.session.query(func.count(FactSales.CustomerKey.distinct())).filter(*filters).scalar() or 0
            
            tot_rev = float(rev_q) + float(ship_q)
            gprofit = tot_rev - float(cogs_q)
            gmargin = (gprofit / tot_rev * 100) if tot_rev > 0 else 0.0
            
            return {
                'rev':    tot_rev,
                'orders': orders_q,
                'custs':  custs_q,
                'profit': gprofit,
                'margin': gmargin
            }

        # Calculate metrics for requested range
        metrics_total = get_wh_metrics(FactSales.DateKey >= start_bound_key)
        
        # Calculate metrics for % change comparison (always this month vs last month)
        metrics_this_mon = get_wh_metrics(FactSales.DateKey >= month_start_key)
        metrics_prev_mon = get_wh_metrics((FactSales.DateKey >= prev_mon_key) & (FactSales.DateKey < month_start_key))

        rev_total    = metrics_total['rev']
        rev_this_mon = metrics_this_mon['rev']
        rev_prev_mon = metrics_prev_mon['rev']

        orders_total    = metrics_total['orders']
        orders_this_mon = metrics_this_mon['orders']
        orders_prev_mon = metrics_prev_mon['orders']

        cust_total    = metrics_total['custs']
        cust_this     = metrics_this_mon['custs']
        cust_prev_mon = metrics_prev_mon['custs']

        gprofit_all  = metrics_total['profit']
        gprofit_this = metrics_this_mon['profit']
        gprofit_prev = metrics_prev_mon['profit']

        gmargin_all  = metrics_total['margin']
        gmargin_this = metrics_this_mon['margin']
        gmargin_prev = metrics_prev_mon['margin']

        # ── ACTIVE PRODUCTS (is_active=True products) ─────────────────────────
        total_products = db.session.query(sfunc.count(Product.id)).filter(Product.is_active == True).scalar() or 0

        # ── INVENTORY VALUE ───────────────────────────────────────────────────
        inventory_value = db.session.query(
            sfunc.sum(Inv.quantity * Product.cost)
        ).join(Product, Inv.product_id == Product.id).scalar() or 0.0

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
        client_retention = (returning / cust_total * 100) if cust_total > 0 else 0.0

        pending_orders = db.session.query(sfunc.count(Order.id)).filter(Order.status == 'Pending').scalar() or 0
        process_alerts = pending_orders + low_stock

        # ── UNMAPPED HISTORICAL REVENUE (ProductKey = 0) — informational only ──
        # These are real Shopify orders whose product could not be resolved in
        # DimProduct. They ARE counted in rev_total above. Shown separately so
        # the user knows how much revenue came from unresolved legacy products.
        unmapped_q = db.session.query(
            sfunc.sum(FactSales.GrossRevenue - FactSales.DiscountAmount).label('rev'),
            sfunc.sum(FactSales.Quantity).label('qty')
        ).filter(FactSales.IsSynthetic == False, FactSales.IsCancelled == False, FactSales.ProductKey == 0).first()
        
        unmapped_rev   = float(unmapped_q.rev or 0.0)
        unmapped_qty   = int(unmapped_q.qty or 0)
        # share relative to the full warehouse revenue (which now includes unmapped)
        unmapped_share = (unmapped_rev / float(rev_total) * 100) if rev_total > 0 else 0.0

        res_dict = {
            'revenue':        {'value': round(float(rev_total), 2),      'period_value': round(float(rev_this_mon), 2),   'change': pct_change(rev_this_mon, rev_prev_mon),      'label': 'all-time revenue'},
            'orders':         {'value': orders_total,                     'period_value': orders_this_mon,                  'change': pct_change(orders_this_mon, orders_prev_mon), 'label': 'all-time orders'},
            'customers':      {'value': cust_total,                  'period_value': cust_this,                    'change': pct_change(cust_this, cust_prev_mon),     'label': 'total customers'},
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
            'resource_allocation': round(min(100.0, (float(transit_value) / 100000.0) * 100), 1),
            'unmapped_stats': {
                'revenue': round(unmapped_rev, 2),
                'units': unmapped_qty,
                'share_pct': round(unmapped_share, 1)
            }
        }
        return jsonify(filter_kpis_by_role(res_dict, current_user.role))
    except Exception as e:
        import traceback
        print(f"KPI ERROR: {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500


@dashboard_bp.route('/sales-trend')
@token_required
def get_sales_trend(current_user):
    """Daily/monthly sales trend for chart. Supports all dashboard date ranges."""
    try:
        period = request.args.get('period', 'all')
        # Map period param to days (period can be '30d','90d','6m','12m','all')
        days_map = {'7d': 7, '30d': 30, '90d': 90, '6m': 180, '12m': 365, 'all': None}
        days = days_map.get(period, None)

        max_datekey = db.session.query(func.max(FactSales.DateKey)).filter(FactSales.IsSynthetic == False).scalar()
        if max_datekey:
            str_dk = str(max_datekey)
            now = datetime(int(str_dk[:4]), int(str_dk[4:6]), int(str_dk[6:]))
        else:
            now = datetime.utcnow()

        base_filters = [FactSales.IsSynthetic == False, FactSales.IsCancelled == False]
        if days:
            start_date = now - timedelta(days=days)
            base_filters.append(DimDate.FullDate >= start_date.date())

        # For long ranges (6m+), aggregate monthly; for short ranges aggregate daily
        use_monthly = period in ('6m', '12m', 'all')

        if use_monthly:
            results = db.session.query(
                DimDate.Year.label('year'),
                DimDate.Month.label('month'),
                DimDate.MonthName.label('month_name'),
                func.sum(FactSales.GrossRevenue - FactSales.DiscountAmount).label('revenue'),
                func.count(func.distinct(FactSales.OrderNumber)).label('orders')
            ).join(DimDate, FactSales.DateKey == DimDate.DateKey
            ).filter(*base_filters
            ).group_by(DimDate.Year, DimDate.Month, DimDate.MonthName
            ).order_by(DimDate.Year, DimDate.Month).all()

            data = [{
                'date': f"{r.year}-{r.month:02d}-01",
                'label': f"{r.month_name[:3]} {r.year}",
                'revenue': round(float(r.revenue or 0), 2),
                'orders': r.orders
            } for r in results]
        else:
            results = db.session.query(
                DimDate.FullDate.label('date'),
                func.sum(FactSales.GrossRevenue - FactSales.DiscountAmount).label('revenue'),
                func.count(func.distinct(FactSales.OrderNumber)).label('orders')
            ).join(DimDate, FactSales.DateKey == DimDate.DateKey
            ).filter(*base_filters
            ).group_by(DimDate.FullDate).order_by('date').all()

            data = [{'date': str(r.date), 'revenue': round(float(r.revenue or 0), 2), 'orders': r.orders}
                    for r in results]

        return jsonify(data)
    except Exception as e:
        import traceback
        print(f"Sales Trend error: {traceback.format_exc()}")
        return jsonify([]), 200


@dashboard_bp.route('/top-products')
@token_required
def get_top_products(current_user):
    """Top 10 best-selling products from operational DB (matches Shopify rankings)."""
    try:
        from app.models import Order, OrderItem, Product
        results = db.session.query(
            Product.id.label('id'),
            Product.name.label('name'),
            Product.sku.label('sku'),
            func.sum(OrderItem.quantity).label('units_sold'),
            func.sum(OrderItem.quantity * OrderItem.unit_price).label('revenue')
        ).join(OrderItem, OrderItem.product_id == Product.id
        ).join(Order, OrderItem.order_id == Order.id
        ).filter(Order.status != 'Cancelled'
        ).group_by(Product.id, Product.name, Product.sku
        ).order_by(db.desc(func.sum(OrderItem.quantity * OrderItem.unit_price))
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
