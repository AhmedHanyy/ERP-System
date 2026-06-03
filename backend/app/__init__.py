from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from .config import Config

db = SQLAlchemy()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Extensions
    db.init_app(app)
    CORS(app, origins=Config.CORS_ORIGINS)

    # Create database schemas if running on PostgreSQL
    with app.app_context():
        db_url = app.config.get('SQLALCHEMY_DATABASE_URI', '')
        if db_url.startswith('postgresql') or db_url.startswith('postgres'):
            from sqlalchemy import text
            try:
                with db.engine.connect() as conn:
                    conn.execute(text("CREATE SCHEMA IF NOT EXISTS operational;"))
                    conn.execute(text("CREATE SCHEMA IF NOT EXISTS warehouse;"))
                    conn.commit()
                print("PostgreSQL schemas 'operational' and 'warehouse' verified/created.")
            except Exception as e:
                print(f"Warning: Could not create schemas automatically: {e}")

    # Register blueprints
    from .routes.auth        import auth_bp
    from .routes.dashboard   import dashboard_bp
    from .routes.orders      import orders_bp
    from .routes.inventory   import inventory_bp
    from .routes.customers   import customers_bp
    from .routes.procurement import procurement_bp
    from .routes.analytics   import analytics_bp
    from .routes.integrations import integrations_bp
    from .routes.admin       import admin_bp

    app.register_blueprint(auth_bp,        url_prefix='/api/auth')
    app.register_blueprint(dashboard_bp,   url_prefix='/api/dashboard')
    app.register_blueprint(orders_bp,      url_prefix='/api/orders')
    app.register_blueprint(inventory_bp,   url_prefix='/api/inventory')
    app.register_blueprint(customers_bp,   url_prefix='/api/customers')
    app.register_blueprint(procurement_bp, url_prefix='/api/procurement')
    app.register_blueprint(analytics_bp,   url_prefix='/api/analytics')
    app.register_blueprint(integrations_bp,url_prefix='/api/integrations')
    app.register_blueprint(admin_bp,       url_prefix='/api/admin')

    # Health check
    @app.route('/api/health')
    def health():
        return {'status': 'ok', 'version': '1.0.0'}

    return app
