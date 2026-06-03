from app import db
from datetime import datetime
import os

DATABASE_URL = os.environ.get('DATABASE_URL', '')
IS_POSTGRES = DATABASE_URL.startswith('postgresql') or DATABASE_URL.startswith('postgres')
SCHEMA_ARGS = {'schema': 'operational'} if IS_POSTGRES else {}


class Inventory(db.Model):
    """
    Stock levels per product.
    NOTE: When real dataset arrives, warehouse_location codes and reorder_point thresholds
    should be calibrated to actual business rules.
    """
    __tablename__ = 'inventory'
    __table_args__ = SCHEMA_ARGS

    id                 = db.Column(db.Integer, primary_key=True)
    product_id         = db.Column(db.Integer, db.ForeignKey('products.id'), unique=True, nullable=False)
    quantity           = db.Column(db.Integer, nullable=False, default=0)
    reorder_point      = db.Column(db.Integer, default=10)    # Trigger procurement suggestion
    reorder_quantity   = db.Column(db.Integer, default=50)    # Suggested order quantity
    warehouse_location = db.Column(db.String(50), nullable=True)
    last_restocked     = db.Column(db.DateTime, nullable=True)
    updated_at         = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    product = db.relationship('Product', back_populates='inventory')

    @property
    def status(self):
        if self.quantity == 0:
            return 'Out of Stock'
        elif self.quantity <= self.reorder_point:
            return 'Low Stock'
        return 'In Stock'

    @property
    def turnover_rate(self):
        """Simplified: units sold / avg inventory (placeholder for real calculation)"""
        return None  # Computed by analytics engine

    def to_dict(self):
        return {
            'id': self.id,
            'product_id': self.product_id,
            'product_name': self.product.name if self.product else None,
            'product_sku': self.product.sku if self.product else None,
            'quantity': self.quantity,
            'reorder_point': self.reorder_point,
            'reorder_quantity': self.reorder_quantity,
            'warehouse_location': self.warehouse_location,
            'status': self.status,
            'last_restocked': self.last_restocked.isoformat() if self.last_restocked else None,
            'updated_at': self.updated_at.isoformat(),
        }


class InventoryLog(db.Model):
    """
    Audit trail for all inventory adjustments.
    NOTE: This is critical for ETL — provides the adjustment history needed for accurate analytics.
    """
    __tablename__ = 'inventory_logs'
    __table_args__ = SCHEMA_ARGS

    id          = db.Column(db.Integer, primary_key=True)
    product_id  = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    change      = db.Column(db.Integer, nullable=False)   # Positive = in, Negative = out
    reason      = db.Column(db.String(200), nullable=True)  # e.g. 'Restock', 'Damage', 'Sale'
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

    product = db.relationship('Product')

    def to_dict(self):
        return {
            'id': self.id,
            'product_id': self.product_id,
            'product_name': self.product.name if self.product else None,
            'change': self.change,
            'reason': self.reason,
            'created_at': self.created_at.isoformat(),
        }
