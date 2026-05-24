"""
Integration stubs for Shopify and WhatsApp (Twilio).
These are fully-wired placeholders — implement real API calls when credentials are available.
"""
from flask import Blueprint, jsonify, request

integrations_bp = Blueprint('integrations', __name__)


@integrations_bp.route('/shopify/webhook', methods=['POST'])
def shopify_webhook():
    """
    TODO: Connect real Shopify webhook
    Events to handle: orders/create, orders/updated, inventory_levels/update
    Docs: https://shopify.dev/docs/api/admin-rest/2024-01/resources/webhook

    Steps to implement:
    1. Verify HMAC signature from Shopify
    2. Parse event type from X-Shopify-Topic header
    3. Map Shopify order schema → SmartERP Order/OrderItem schema
    4. Insert/update records in DB
    """
    topic = request.headers.get('X-Shopify-Topic', 'unknown')
    data  = request.get_json(silent=True)
    return jsonify({
        'status': 'stub',
        'message': f'Shopify webhook received: {topic}. Real integration pending.',
        'received_payload_keys': list(data.keys()) if data else []
    })


@integrations_bp.route('/whatsapp/notify', methods=['POST'])
def whatsapp_notify():
    """
    TODO: Connect real Twilio WhatsApp API
    Use case: Notify supplier when a procurement request is created/sent

    Steps to implement:
    1. pip install twilio
    2. Set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_FROM in .env
    3. Replace stub below with:

        from twilio.rest import Client
        client = Client(current_app.config['TWILIO_ACCOUNT_SID'],
                        current_app.config['TWILIO_AUTH_TOKEN'])
        message = client.messages.create(
            from_=f"whatsapp:{current_app.config['TWILIO_WHATSAPP_FROM']}",
            to=f"whatsapp:{supplier_whatsapp_number}",
            body=message_body
        )
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
def shopify_sync():
    """
    TODO: Full bidirectional sync
    - Pull orders from Shopify REST API (paginated)
    - Pull product inventory from Shopify
    - Push low-stock updates back to Shopify
    """
    return jsonify({
        'status': 'stub',
        'message': 'Shopify full sync — pending real API credentials'
    })
