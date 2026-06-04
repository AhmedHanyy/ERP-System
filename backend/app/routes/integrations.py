"""
Integration stubs for Shopify and WhatsApp (Twilio).
These are fully-wired placeholders — implement real API calls when credentials are available.
"""
from flask import Blueprint, jsonify, request
from .auth import token_required, roles_required

integrations_bp = Blueprint('integrations', __name__)


@integrations_bp.route('/shopify/webhook', methods=['POST'])
def shopify_webhook():
    """
    Real-time Shopify Webhook Handler.
    Supports: orders/create (creates customer, orders, order items, adjusts inventory, triggers ETL).
    """
    from app import db
    from app.models import Customer, Order, OrderItem, Product, Inventory, InventoryLog, AuditLog
    import threading
    from flask import current_app
    from app.analytics.etl_pipeline import run_etl_pipeline
    from datetime import datetime

    topic = request.headers.get('X-Shopify-Topic', 'unknown')
    data  = request.get_json(silent=True) or {}

    if topic == 'orders/create':
        try:
            # 1. Parse / Create Customer
            email = (data.get('email') or 'unknown@leveld.store').lower().strip()
            cust = Customer.query.filter_by(email=email).first()
            if not cust:
                first_name = data.get('customer', {}).get('first_name', 'Shopify')
                last_name  = data.get('customer', {}).get('last_name', 'User')
                cust = Customer(
                    name=f"{first_name} {last_name}".strip(),
                    email=email,
                    phone=data.get('customer', {}).get('phone') or data.get('billing_address', {}).get('phone'),
                    city=data.get('billing_address', {}).get('city') or 'Cairo',
                    address=data.get('billing_address', {}).get('address1') or 'Shopify Order Address',
                    country=data.get('billing_address', {}).get('country_code') or 'EG',
                    segment='New'
                )
                db.session.add(cust)
                db.session.flush()

            # 2. Parse / Create Order
            # Calculate total_amount = subtotal + shipping - discount
            subtotal = float(data.get('subtotal_price') or 0.0)
            shipping = float(data.get('total_shipping_price_set', {}).get('shop_money', {}).get('amount') or 50.0)
            discount = float(data.get('total_discounts') or 0.0)
            total = subtotal + shipping - discount

            order = Order(
                order_number=data.get('name') or f"#SHPF-{data.get('id')}",
                customer_id=cust.id,
                status='Pending',
                total_amount=total,
                discount=discount,
                shipping_fee=shipping,
                notes=data.get('note') or 'Created via Shopify webhook',
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.session.add(order)
            db.session.flush()

            # 3. Create Line Items and Adjust Inventory
            for item in data.get('line_items', []):
                sku = item.get('sku') or ''
                product = Product.query.filter_by(sku=sku).first()
                if not product:
                    # Fallback lookup by title
                    product = Product.query.filter(Product.name.ilike(f"%{item.get('title')}%")).first()
                
                if product:
                    # Create OrderItem
                    qty = int(item.get('quantity') or 1)
                    price = float(item.get('price') or 0.0)
                    order_item = OrderItem(
                        order_id=order.id,
                        product_id=product.id,
                        quantity=qty,
                        unit_price=price
                    )
                    db.session.add(order_item)

                    # Deduct from Inventory
                    inv = Inventory.query.filter_by(product_id=product.id).first()
                    if inv:
                        old_qty = inv.quantity
                        inv.quantity = max(0, inv.quantity - qty)
                        inv.updated_at = datetime.utcnow()
                        db.session.add(InventoryLog(
                            product_id=product.id,
                            change=-qty,
                            reason=f"Shopify Order {order.order_number}"
                        ))
                        db.session.add(AuditLog(
                            user_id=1,  # System user ID stub
                            action=f"Auto-deducted inventory via Shopify Webhook Order {order.order_number}",
                            target_table="inventory",
                            target_id=inv.id,
                            old_value=str(old_qty),
                            new_value=str(inv.quantity)
                        ))

            db.session.commit()

            # 4. Trigger Warehouse ETL Refresh Asynchronously
            app_obj = current_app._get_current_object()
            def run_sync(app):
                with app.app_context():
                    run_etl_pipeline()
            threading.Thread(target=run_sync, args=(app_obj,)).start()

            return jsonify({
                'status': 'success',
                'message': f"Order {order.order_number} created, inventory adjusted, and warehouse sync triggered."
            }), 201

        except Exception as e:
            db.session.rollback()
            return jsonify({
                'status': 'error',
                'message': f"Failed to parse and insert Shopify webhook order: {str(e)}"
            }), 500

    return jsonify({
        'status': 'stub',
        'message': f'Shopify webhook received topic: {topic}. Real-time order creation is fully operational; other webhooks pending details.',
        'received_payload_keys': list(data.keys()) if data else []
    })


@integrations_bp.route('/whatsapp/notify', methods=['POST'])
@roles_required('Admin', 'Procurement Staff', 'Procurement Officer', 'Operations Manager')
def whatsapp_notify(current_user):
    """
    TODO: Connect real Twilio WhatsApp API
    """
    data = request.get_json(silent=True)
    to   = data.get('to', '') if data else ''
    body = data.get('body', '') if data else ''

    return jsonify({
        'status': 'stub',
        'message': f'WhatsApp notification would be sent to {to}: "{body}"',
        'integration': 'Twilio WhatsApp — pending credentials'
    })


@integrations_bp.route('/shopify/sync', methods=['POST'])
@roles_required('Admin')
def shopify_sync(current_user):
    import threading
    from flask import current_app
    from app.analytics.etl_pipeline import run_etl_pipeline
    
    app = current_app._get_current_object()
    
    def run_sync(app_obj):
        with app_obj.app_context():
            run_etl_pipeline()
            
    threading.Thread(target=run_sync, args=(app,)).start()
    
    return jsonify({
        'status': 'success',
        'message': 'Shopify CSV synchronization and Data Warehouse refresh started in the background.'
    })
