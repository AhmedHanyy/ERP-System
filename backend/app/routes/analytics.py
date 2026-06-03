from flask import Blueprint, jsonify, request
from app.analytics.forecasting  import forecast_overall_revenue, forecast_product_demand
from app.analytics.segmentation import compute_rfm
from app.analytics.association  import run_market_basket, get_product_recommendations
from app.analytics.etl import get_daily_sales_df, get_product_sales_df
from app import db
from app.models import Order, OrderItem, Product, Inventory, Supplier, ProcurementRequest, Customer, Notification, AuditLog
from sqlalchemy import func
from datetime import datetime, timedelta
import math

analytics_bp = Blueprint('analytics', __name__)

@analytics_bp.route('/forecast')
def revenue_forecast():
    days = request.args.get('days', 30, type=int)
    return jsonify(forecast_overall_revenue(days_ahead=days))

@analytics_bp.route('/market-basket')
def market_basket():
    min_support = request.args.get('min_support', 0.02, type=float)
    min_confidence = request.args.get('min_confidence', 0.3, type=float)
    return jsonify(run_market_basket(min_support=min_support, min_confidence=min_confidence))

@analytics_bp.route('/procurement-engine')
def smart_procurement():
    """Predictive engine for reordering."""
    items = db.session.query(Product, Inventory).join(Inventory).all()
    suggestions = []
    
    for p, inv in items:
        # Get demand forecast for this product
        forecast = forecast_product_demand(p.id, days_ahead=30)
        daily_avg = forecast.get('total_forecasted_units', 0) / 30
        
        if daily_avg > 0:
            stockout_days = inv.quantity / daily_avg
            stockout_date = datetime.utcnow() + timedelta(days=stockout_days)
        else:
            stockout_days = 999
            stockout_date = None
            
        # Decision logic
        if stockout_days < 10 or inv.quantity <= inv.reorder_point:
            suggestions.append({
                'product_id': p.id,
                'name': p.name,
                'current_stock': inv.quantity,
                'suggested_qty': inv.reorder_quantity,
                'stockout_days': round(stockout_days, 1),
                'stockout_date': stockout_date.isoformat() if stockout_date else "Safe",
                'priority': 'High' if stockout_days < 5 else 'Medium'
            })
            
    return jsonify(suggestions)

@analytics_bp.route('/bi-report')
def bi_report():
    # ABC & Safety Stock (as before)
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
def get_notifications():
    role = request.args.get('role')
    notifs = Notification.query.filter(
        (Notification.recipient_role == role) | (Notification.recipient_role == None)
    ).order_by(Notification.created_at.desc()).limit(20).all()
    return jsonify([n.to_dict() for n in notifs])

@analytics_bp.route('/audit-logs')
def get_audit_logs():
    logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(100).all()
    return jsonify([l.to_dict() for l in logs])
