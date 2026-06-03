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
    TODO: Connect real Shopify webhook
    Events to handle: orders/create, orders/updated, inventory_levels/update
    Docs: https://shopify.dev/docs/api/admin-rest/2024-01/resources/webhook
    """
    topic = request.headers.get('X-Shopify-Topic', 'unknown')
    data  = request.get_json(silent=True)
    return jsonify({
        'status': 'stub',
        'message': f'Shopify webhook received: {topic}. Real integration pending.',
        'received_payload_keys': list(data.keys()) if data else []
    })


@integrations_bp.route('/whatsapp/notify', methods=['POST'])
@roles_required('Admin', 'Procurement Staff', 'Operations Manager')
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
