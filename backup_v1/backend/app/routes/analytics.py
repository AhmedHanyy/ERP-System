from flask import Blueprint, jsonify, request
from app.analytics.forecasting  import forecast_overall_revenue, forecast_product_demand
from app.analytics.segmentation import compute_rfm
from app.analytics.association  import run_market_basket, get_product_recommendations
from app.analytics.etl import get_daily_sales_df, get_product_sales_df
from app import db
from app.models import Order, OrderItem, Product, Inventory, Supplier, ProcurementRequest
from sqlalchemy import func

analytics_bp = Blueprint('analytics', __name__)


@analytics_bp.route('/forecast')
def revenue_forecast():
    days = request.args.get('days', 30, type=int)
    return jsonify(forecast_overall_revenue(days_ahead=days))


@analytics_bp.route('/forecast/product/<int:product_id>')
def product_forecast(product_id):
    days = request.args.get('days', 30, type=int)
    return jsonify(forecast_product_demand(product_id=product_id, days_ahead=days))


@analytics_bp.route('/rfm')
def rfm_analysis():
    return jsonify(compute_rfm())


@analytics_bp.route('/market-basket')
def market_basket():
    min_support    = request.args.get('min_support', 0.02, type=float)
    min_confidence = request.args.get('min_confidence', 0.3, type=float)
    return jsonify(run_market_basket(min_support=min_support, min_confidence=min_confidence))


@analytics_bp.route('/recommendations/<string:product_name>')
def recommendations(product_name):
    return jsonify(get_product_recommendations(product_name))


@analytics_bp.route('/bi-report')
def bi_report():
    """BI dashboard data: P&L, category performance, supplier stats, Pareto."""
    # Category revenue (for treemap)
    cat_data = db.session.query(
        Product.category_id,
        func.sum(OrderItem.quantity * OrderItem.unit_price).label('revenue'),
        func.sum(OrderItem.quantity).label('units')
    ).join(OrderItem, Product.id == OrderItem.product_id
    ).join(Order, OrderItem.order_id == Order.id
    ).filter(Order.status != 'Cancelled'
    ).group_by(Product.category_id).all()

    # Pareto analysis (top products = 80% of revenue)
    product_df = get_product_sales_df()
    if not product_df.empty:
        total_rev = product_df['revenue'].sum()
        product_df['cum_revenue_pct'] = (product_df['revenue'].cumsum() / total_rev * 100).round(2)
        pareto = product_df.head(20).to_dict(orient='records')
    else:
        pareto = []

    # Supplier performance
    supplier_perf = db.session.query(
        Supplier.id,
        Supplier.name,
        Supplier.rating,
        func.count(ProcurementRequest.id).label('total_orders'),
        func.sum(ProcurementRequest.total_cost).label('total_value'),
    ).join(ProcurementRequest, Supplier.id == ProcurementRequest.supplier_id, isouter=True
    ).group_by(Supplier.id).all()

    # Monthly revenue (last 12 months)
    from datetime import datetime, timedelta
    year_ago = datetime.utcnow() - timedelta(days=365)
    monthly = db.session.query(
        func.strftime('%Y-%m', Order.created_at).label('month'),
        func.sum(Order.total_amount).label('revenue'),
        func.count(Order.id).label('orders')
    ).filter(Order.created_at >= year_ago, Order.status != 'Cancelled'
    ).group_by('month').order_by('month').all()

    return jsonify({
        'category_revenue': [
            {'category_id': r.category_id, 'revenue': round(float(r.revenue or 0), 2), 'units': int(r.units or 0)}
            for r in cat_data
        ],
        'pareto_analysis': [
            {k: (round(v, 2) if isinstance(v, float) else v) for k, v in p.items()}
            for p in pareto
        ],
        'supplier_performance': [
            {
                'id': r.id, 'name': r.name, 'rating': r.rating,
                'total_orders': r.total_orders or 0,
                'total_value': round(float(r.total_value or 0), 2)
            }
            for r in supplier_perf
        ],
        'monthly_revenue': [
            {'month': r.month, 'revenue': round(float(r.revenue or 0), 2), 'orders': r.orders}
            for r in monthly
        ],
    })


@analytics_bp.route('/etl-status')
def etl_status():
    """ETL pipeline status overview (conceptual pipeline display)."""
    from app.models import Customer, Inventory
    return jsonify({
        'pipeline': [
            {'stage': 'Extract',   'status': 'active', 'description': 'Pulling from OLTP (SQLite/PostgreSQL)'},
            {'stage': 'Transform', 'status': 'active', 'description': 'Cleaning, normalizing, adding date features'},
            {'stage': 'Load',      'status': 'active', 'description': 'Aggregating into analytics DataFrames'},
            {'stage': 'Analyze',   'status': 'active', 'description': 'Forecasting + RFM + Association Rules'},
        ],
        'data_counts': {
            'orders':     Order.query.count(),
            'customers':  Customer.query.count(),
            'products':   Product.query.count(),
            'inventory':  Inventory.query.count(),
        },
        'last_run': 'On-demand (real-time computation)',
    })
