from flask import Blueprint, jsonify, request
from app.analytics.forecasting  import forecast_overall_revenue, forecast_product_demand
from app.analytics.segmentation import compute_rfm
from app.analytics.association  import run_market_basket, get_product_recommendations
from app.analytics.etl import (
    get_daily_sales_df, get_product_sales_df,
    get_discount_performance_df, get_geographic_sales_df,
)
from app import db
from app.models import Order, OrderItem, Product, Inventory, Supplier, ProcurementRequest, Customer, Notification, AuditLog
from sqlalchemy import func
from datetime import datetime, timedelta
import math
from .auth import token_required, roles_required

analytics_bp = Blueprint('analytics', __name__)

@analytics_bp.route('/forecast')
@roles_required('Admin', 'Analytics Manager')
def revenue_forecast(current_user):
    days = request.args.get('days', 30, type=int)
    return jsonify(forecast_overall_revenue(days_ahead=days))

@analytics_bp.route('/forecast/product/<int:product_id>')
@roles_required('Admin', 'Analytics Manager')
def product_demand_forecast(current_user, product_id):
    days = request.args.get('days', 30, type=int)
    return jsonify(forecast_product_demand(product_id, days_ahead=days))

@analytics_bp.route('/rfm')
@roles_required('Admin', 'Analytics Manager')
def get_rfm(current_user):
    return jsonify(compute_rfm())

@analytics_bp.route('/customer-insights/<int:customer_id>')
@roles_required('Admin', 'Customer Service', 'Analytics Manager')
def customer_insights(current_user, customer_id):
    customer = Customer.query.get_or_404(customer_id)
    orders = Order.query.filter(Order.customer_id == customer_id, Order.status != 'Cancelled').all()
    
    if not orders:
        return jsonify({
            'behavior_report': {
                'order_consistency': 'Irregular',
                'avg_basket_value': 0,
                'prediction': 'Unknown'
            },
            'top_products': []
        })
    
    avg_basket = sum(o.total_amount for o in orders) / len(orders)
    
    if len(orders) > 5:
        import numpy as np
        order_dates = sorted([o.created_at for o in orders])
        intervals = [(order_dates[i] - order_dates[i-1]).days for i in range(1, len(order_dates))]
        if intervals:
            std_dev = np.std(intervals) if len(intervals) > 1 else 0
            consistency = "Consistent" if std_dev < 10 else "Periodic"
        else:
            consistency = "Periodic"
    elif len(orders) >= 2:
        consistency = "Periodic"
    else:
        consistency = "Irregular"
        
    last_order_date = max(o.created_at for o in orders)
    days_since_last = (datetime.utcnow() - last_order_date).days
    if days_since_last > 90:
        prediction = "High Churn Risk"
    elif days_since_last <= 30:
        prediction = "Low Churn Risk"
    else:
        prediction = "Medium Churn Risk"
        
    order_ids = [o.id for o in orders]
    items = db.session.query(
        Product.name,
        func.sum(OrderItem.quantity).label('qty'),
        func.sum(OrderItem.quantity * OrderItem.unit_price).label('spend')
    ).join(OrderItem, Product.id == OrderItem.product_id)\
     .filter(OrderItem.order_id.in_(order_ids))\
     .group_by(Product.name)\
     .order_by(db.desc('spend'))\
     .all()
     
    top_products = [
        {
            'name': name,
            'qty': int(qty or 0),
            'spend': round(float(spend or 0), 2)
        } for name, qty, spend in items
    ]
    
    return jsonify({
        'behavior_report': {
            'order_consistency': consistency,
            'avg_basket_value': round(avg_basket, 2),
            'prediction': prediction
        },
        'top_products': top_products
    })

@analytics_bp.route('/market-basket')
@roles_required('Admin', 'Analytics Manager')
def market_basket(current_user):
    min_support = request.args.get('min_support', 0.02, type=float)
    min_confidence = request.args.get('min_confidence', 0.3, type=float)
    return jsonify(run_market_basket(min_support=min_support, min_confidence=min_confidence))

@analytics_bp.route('/procurement-engine')
@roles_required('Admin', 'Procurement Staff', 'Operations Manager')
def smart_procurement(current_user):
    """Predictive engine for reordering."""
    items = db.session.query(Product, Inventory).join(Inventory).all()
    suggestions = []
    
    for p, inv in items:
        forecast = forecast_product_demand(p.id, days_ahead=30)
        daily_avg = forecast.get('total_forecasted_units', 0) / 30
        
        if daily_avg > 0:
            stockout_days = inv.quantity / daily_avg
            stockout_date = datetime.utcnow() + timedelta(days=stockout_days)
        else:
            stockout_days = 999
            stockout_date = None
            
        if stockout_days < 10 or inv.quantity <= inv.reorder_point:
            last_req = ProcurementRequest.query.filter_by(
                product_id=p.id, status='Received'
            ).order_by(ProcurementRequest.requested_at.desc()).first()
            
            pref_supplier = None
            if last_req:
                pref_supplier = last_req.supplier
            else:
                pref_supplier = Supplier.query.filter_by(is_active=True).order_by(Supplier.rating.desc()).first()
                
            supplier_id = pref_supplier.id if pref_supplier else None
            supplier_name = pref_supplier.name if pref_supplier else "Unknown Supplier"
            lead_time = pref_supplier.lead_time_days if pref_supplier else 7
            
            if stockout_date:
                reorder_date = stockout_date - timedelta(days=lead_time)
                reorder_date_str = str(reorder_date.date())
                stockout_date_str = str(stockout_date.date())
            else:
                reorder_date_str = "Immediate"
                stockout_date_str = "Critical"
                
            suggestions.append({
                'product_id': p.id,
                'name': p.name,
                'current_stock': inv.quantity,
                'suggested_qty': inv.reorder_quantity,
                'stockout_days': round(stockout_days, 1),
                'stockout_date': stockout_date_str,
                'suggested_reorder_date': reorder_date_str,
                'recommended_supplier_id': supplier_id,
                'recommended_supplier_name': supplier_name,
                'priority': 'High' if stockout_days < 5 else 'Medium'
            })
            
    return jsonify(suggestions)

@analytics_bp.route('/bi-report')
@roles_required('Admin', 'Analytics Manager')
def bi_report(current_user):
    product_df_list = get_product_sales_df().to_dict(orient='records')
    abc_report = []
    if product_df_list:
        total_revenue = sum(p['revenue'] for p in product_df_list)
        sorted_products = sorted(product_df_list, key=lambda x: x['revenue'], reverse=True)
        cum_rev = 0
        for p in sorted_products:
            cum_rev += p['revenue']
            pct = (cum_rev / total_revenue) * 100 if total_revenue > 0 else 0
            p['abc_class'] = 'A' if pct <= 80 else 'B' if pct <= 95 else 'C'
            abc_report.append(p)

    return jsonify({
        'abc_analysis': abc_report[:30],
        'financial_summary': { 'total_revenue': sum(p['revenue'] for p in abc_report) }
    })

@analytics_bp.route('/notifications')
@token_required
def get_notifications(current_user):
    notifs = Notification.query.filter(
        (Notification.recipient_role == current_user.role) | (Notification.recipient_role == None)
    ).order_by(Notification.created_at.desc()).limit(20).all()
    return jsonify([n.to_dict() for n in notifs])

@analytics_bp.route('/notifications/clear', methods=['POST'])
@token_required
def clear_notifications(current_user):
    notifs = Notification.query.filter(
        (Notification.recipient_role == current_user.role) | (Notification.recipient_role == None)
    ).all()
    for n in notifs:
        n.is_read = True
    db.session.commit()
    
    # Audit log
    log = AuditLog(
        user_id=current_user.id, 
        action="Cleared notifications", 
        target_table="notifications"
    )
    db.session.add(log)
    db.session.commit()
    
    return jsonify({'status': 'success', 'message': 'All notifications marked as read'})

@analytics_bp.route('/notifications/<int:notif_id>', methods=['PATCH'])
@token_required
def mark_notification_read(current_user, notif_id):
    n = Notification.query.get_or_404(notif_id)
    n.is_read = True
    db.session.commit()
    return jsonify(n.to_dict())

@analytics_bp.route('/audit-logs')
@roles_required('Admin')
def get_audit_logs(current_user):
    logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(100).all()
    return jsonify([l.to_dict() for l in logs])

@analytics_bp.route('/etl/status')
@roles_required('Admin', 'Analytics Manager')
def etl_status(current_user):
    from app.models.warehouse import ETLRun, FactSales, DimCustomer
    latest_run = ETLRun.query.order_by(ETLRun.start_time.desc()).first()

    sales_count = real_count = synth_count = cust_count = fraud_count = 0
    try:
        sales_count  = FactSales.query.count()
        real_count   = FactSales.query.filter_by(IsSynthetic=False).count()
        synth_count  = FactSales.query.filter_by(IsSynthetic=True).count()
        cust_count   = DimCustomer.query.count()
        fraud_count  = DimCustomer.query.filter_by(IsFraudRisk=True).count()
    except Exception as e:
        print(f'Error reading counts: {e}')

    return jsonify({
        'last_run': latest_run.to_dict() if latest_run else None,
        'data_counts': {
            'total_sales_rows':   sales_count,
            'real_sales_rows':    real_count,
            'synthetic_rows':     synth_count,
            'customers':          cust_count,
            'fraud_risk_customers': fraud_count,
        },
        'data_quality': {
            'synthetic_pct': round(synth_count / sales_count * 100, 1) if sales_count else 0,
            'note': 'Synthetic records are for ML training only. All dashboards use IsSynthetic=False.'
        }
    })

@analytics_bp.route('/etl/run', methods=['POST'])
@roles_required('Admin')
def trigger_etl(current_user):
    import threading
    from flask import current_app
    from app.models.warehouse import ETLRun

    active_run = ETLRun.query.filter_by(status='Running').first()
    if active_run:
        return jsonify({'status': 'error', 'message': 'ETL pipeline is already running.'}), 400

    app = current_app._get_current_object()

    def background_etl(app_obj):
        with app_obj.app_context():
            from app.analytics.etl_pipeline import run_etl_pipeline
            run_etl_pipeline()

    threading.Thread(target=background_etl, args=(app,)).start()
    return jsonify({'status': 'success', 'message': 'ETL pipeline triggered in the background.'})


@analytics_bp.route('/discount-performance')
@roles_required('Admin', 'Analytics Manager')
def discount_performance(current_user):
    """Real discount code performance (LEVELD10, FREESHIPPING, No Discount)."""
    try:
        df = get_discount_performance_df()
        return jsonify(df.to_dict(orient='records'))
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@analytics_bp.route('/geographic-sales')
@roles_required('Admin', 'Analytics Manager')
def geographic_sales(current_user):
    """Sales by Egyptian governorate (real orders only)."""
    try:
        df = get_geographic_sales_df()
        return jsonify(df.to_dict(orient='records'))
    except Exception as e:
        return jsonify({'error': str(e)}), 500
