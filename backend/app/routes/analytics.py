from flask import Blueprint, jsonify, request
from app.analytics.forecasting  import forecast_overall_revenue, forecast_product_demand
from app.analytics.segmentation import compute_rfm
from app.analytics.association  import run_market_basket, get_product_recommendations
from app.analytics.etl import get_daily_sales_df, get_product_sales_df
from app import db
from app.models import Order, OrderItem, Product, Inventory, Supplier, ProcurementRequest, Customer
from sqlalchemy import func
from datetime import datetime, timedelta
import math

analytics_bp = Blueprint('analytics', __name__)


@analytics_bp.route('/forecast')
def revenue_forecast():
    """Predictive revenue modeling."""
    days = request.args.get('days', 30, type=int)
    return jsonify(forecast_overall_revenue(days_ahead=days))


@analytics_bp.route('/rfm')
def rfm_analysis():
    """Customer clustering engine."""
    return jsonify(compute_rfm())


@analytics_bp.route('/market-basket')
def market_basket():
    """Association rule mining."""
    min_support    = request.args.get('min_support', 0.02, type=float)
    min_confidence = request.args.get('min_confidence', 0.3, type=float)
    return jsonify(run_market_basket(min_support=min_support, min_confidence=min_confidence))


@analytics_bp.route('/bi-report')
def bi_report():
    """Sophisticated BI report with ABC, Safety Stock, and Financial informatics."""
    # 1. ABC Classification logic (Pure Python fallback)
    product_df_list = get_product_sales_df().to_dict(orient='records')
    abc_report = []
    if product_df_list:
        total_revenue = sum(p['revenue'] for p in product_df_list)
        sorted_products = sorted(product_df_list, key=lambda x: x['revenue'], reverse=True)
        
        cum_rev = 0
        for p in sorted_products:
            cum_rev += p['revenue']
            pct = (cum_rev / total_revenue) * 100 if total_revenue > 0 else 0
            
            p['abc_class'] = 'A (High Value)' if pct <= 80 else 'B (Medium)' if pct <= 95 else 'C (Long Tail)'
            abc_report.append(p)

    # 2. Safety Stock (Pure Python)
    inventory_items = db.session.query(Product, Inventory).join(Inventory).all()
    safety_stock_report = []
    for p, inv in inventory_items:
        demand_std_dev = (p.price / 100) * 2 
        lead_time_days = 7
        safety_stock = int(round(1.65 * demand_std_dev * math.sqrt(lead_time_days)))
        
        safety_stock_report.append({
            'product_id': p.id,
            'name': p.name,
            'current_stock': inv.quantity,
            'safety_stock': safety_stock,
            'status': 'Healthy' if inv.quantity > safety_stock else 'Risk'
        })

    # 3. Monthly Performance Trend
    year_ago = datetime.utcnow() - timedelta(days=365)
    monthly = db.session.query(
        func.strftime('%Y-%m', Order.created_at).label('month'),
        func.sum(Order.total_amount).label('revenue'),
        func.count(Order.id).label('orders')
    ).filter(Order.created_at >= year_ago, Order.status != 'Cancelled'
    ).group_by('month').order_by('month').all()

    # 4. Financials & Regional
    cat_data = db.session.query(
        Product.category_id,
        func.sum(OrderItem.quantity * OrderItem.unit_price).label('revenue'),
        func.sum(OrderItem.quantity * Product.cost).label('cogs')
    ).join(OrderItem, Product.id == OrderItem.product_id).join(Order, OrderItem.order_id == Order.id).filter(Order.status != 'Cancelled').group_by(Product.category_id).all()

    region_data = db.session.query(Customer.city, func.sum(Order.total_amount).label('revenue')).join(Order, Customer.id == Order.customer_id).filter(Order.status != 'Cancelled').group_by(Customer.city).all()
    
    total_rev = sum(float(r.revenue or 0) for r in cat_data)
    total_cogs = sum(float(r.cogs or 0) for r in cat_data)
    
    return jsonify({
        'financial_summary': {
            'total_revenue': round(total_rev, 2),
            'total_cogs': round(total_cogs, 2),
            'gross_profit': round(total_rev - total_cogs, 2),
            'gross_margin_pct': round(((total_rev - total_cogs) / total_rev * 100) if total_rev > 0 else 0, 2)
        },
        'abc_analysis': abc_report[:30],
        'safety_stock_report': safety_stock_report,
        'monthly_revenue': [{'month': r.month, 'revenue': round(float(r.revenue or 0), 2), 'orders': r.orders} for r in monthly],
        'region_distribution': [{'city': r.city or 'Unknown', 'revenue': float(r.revenue or 0)} for r in region_data],
        'category_performance': [
            {'category_id': r.category_id, 'revenue': float(r.revenue or 0), 'margin_pct': round(((float(r.revenue or 0) - float(r.cogs or 0)) / float(r.revenue or 1)) * 100, 2)}
            for r in cat_data
        ]
    })


@analytics_bp.route('/customer-insights/<int:customer_id>')
def customer_insights(customer_id):
    """Deep informatics with pure Python fallback."""
    customer = Customer.query.get_or_404(customer_id)
    
    top_products = db.session.query(
        Product.name,
        func.sum(OrderItem.quantity).label('total_qty'),
        func.sum(OrderItem.quantity * OrderItem.unit_price).label('total_spend')
    ).join(OrderItem, Product.id == OrderItem.product_id).join(Order, OrderItem.order_id == Order.id
    ).filter(Order.customer_id == customer_id, Order.status != 'Cancelled'
    ).group_by(Product.id).order_by(db.desc('total_spend')).all()

    orders = Order.query.filter_by(customer_id=customer_id).all()
    if orders:
        avg_basket = sum(o.total_amount for o in orders) / len(orders)
        intervals = []
        for i in range(1, len(orders)):
            delta = (orders[i].created_at - orders[i-1].created_at).days
            intervals.append(delta)
        consistency = "High" if (intervals and (sum(intervals)/len(intervals)) < 20) else "Moderate" if intervals else "Unknown"
    else:
        avg_basket = 0
        consistency = "New"

    return jsonify({
        'top_products': [{'name': r.name, 'qty': int(r.total_qty), 'spend': float(r.total_spend)} for r in top_products],
        'behavior_report': {
            'avg_basket_value': round(avg_basket, 2),
            'order_consistency': consistency,
            'prediction': 'High LTV Potential' if avg_basket > 2000 else 'Stable Consumer'
        }
    })
