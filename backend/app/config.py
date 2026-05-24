import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'smarterp-dev-secret-change-in-production')
    # ─── Database ─────────────────────────────────────────────────────────────
    # Currently: SQLite (zero-setup, great for dev/demo)
    # To switch to PostgreSQL: change to postgresql://user:pass@host/dbname
    # This is the ONLY line you need to change when migrating.
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        f'sqlite:///{os.path.join(BASE_DIR, "..", "smarterp.db")}'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False

    # ─── CORS ─────────────────────────────────────────────────────────────────
    CORS_ORIGINS = ['http://localhost:5173', 'http://127.0.0.1:5173']

    # ─── Future Integrations (stubs) ──────────────────────────────────────────
    # TODO: Add real keys when integrating
    SHOPIFY_API_KEY    = os.environ.get('SHOPIFY_API_KEY', '')
    SHOPIFY_SHOP_URL   = os.environ.get('SHOPIFY_SHOP_URL', '')
    TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID', '')
    TWILIO_AUTH_TOKEN  = os.environ.get('TWILIO_AUTH_TOKEN', '')
    TWILIO_WHATSAPP_FROM = os.environ.get('TWILIO_WHATSAPP_FROM', '')
