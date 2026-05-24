from app import db
from datetime import datetime


class Order(db.Model):
    """
    Sales orders (OLTP).
    Status pipeline: Pending → Preparing → Shipped → Delivered / Cancelled
    NOTE: When real Shopify data arrives, map Shopify order fields to this schema.
    """
    __tablename__ = 'orders'

    STATUS_CHOICES = ['Pending', 'Preparing', 'Shipped', 'Delivered', 'Cancelled']

    id           = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(20), unique=True, nullable=False)
    customer_id  = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    status       = db.Column(db.String(30), default='Pending', nullable=False)
    total_amount = db.Column(db.Float, nullable=False, default=0.0)
    discount     = db.Column(db.Float, default=0.0)
    shipping_fee = db.Column(db.Float, default=0.0)
    notes        = db.Column(db.Text, nullable=True)
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at   = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    customer     = db.relationship('Customer', back_populates='orders')
    items        = db.relationship('OrderItem', back_populates='order', cascade='all, delete-orphan')

    @property
    def profit(self):
        return sum(
            (item.unit_price - item.product.cost) * item.quantity
            for item in self.items if item.product
        )

    def to_dict(self, include_items=False):
        d = {
            'id': self.id,
            'order_number': self.order_number,
            'customer_id': self.customer_id,
            'customer_name': self.customer.name if self.customer else None,
            'customer_email': self.customer.email if self.customer else None,
            'status': self.status,
            'total_amount': round(self.total_amount, 2),
            'discount': self.discount,
            'shipping_fee': self.shipping_fee,
            'profit': round(self.profit, 2),
            'notes': self.notes,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
        }
        if include_items:
            d['items'] = [item.to_dict() for item in self.items]
        return d


class OrderItem(db.Model):
    """
    Individual line items within an order.
    NOTE: Unit price is stored at time of sale (not live product price) — important for historical accuracy.
    """
    __tablename__ = 'order_items'

    id         = db.Column(db.Integer, primary_key=True)
    order_id   = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity   = db.Column(db.Integer, nullable=False, default=1)
    unit_price = db.Column(db.Float, nullable=False)   # Price at time of sale

    order   = db.relationship('Order', back_populates='items')
    product = db.relationship('Product', back_populates='order_items')

    @property
    def subtotal(self):
        return round(self.unit_price * self.quantity, 2)

    def to_dict(self):
        return {
            'id': self.id,
            'order_id': self.order_id,
            'product_id': self.product_id,
            'product_name': self.product.name if self.product else None,
            'product_sku': self.product.sku if self.product else None,
            'quantity': self.quantity,
            'unit_price': self.unit_price,
            'subtotal': self.subtotal,
        }
