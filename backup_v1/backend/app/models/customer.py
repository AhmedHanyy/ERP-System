from app import db
from datetime import datetime


class Customer(db.Model):
    """
    Customer profiles (OLTP layer).
    NOTE: When real dataset arrives, address format, segmentation logic, and LTV calculation
    may need to be recalibrated based on actual customer data structure.
    """
    __tablename__ = 'customers'
    id         = db.Column(db.Integer, primary_key=True)
    name       = db.Column(db.String(150), nullable=False)
    email      = db.Column(db.String(200), unique=True, nullable=False)
    phone      = db.Column(db.String(30), nullable=True)
    address    = db.Column(db.Text, nullable=True)
    city       = db.Column(db.String(100), nullable=True)
    country    = db.Column(db.String(100), default='Egypt')
    segment    = db.Column(db.String(50), default='New')   # Set by RFM analytics
    rfm_score  = db.Column(db.Float, nullable=True)        # Computed by analytics engine
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    orders     = db.relationship('Order', back_populates='customer', lazy='dynamic')

    @property
    def total_orders(self):
        return self.orders.count()

    @property
    def lifetime_value(self):
        return sum(o.total_amount for o in self.orders if o.status != 'Cancelled')

    @property
    def last_order_date(self):
        last = self.orders.order_by(db.desc('created_at')).first()
        return last.created_at.isoformat() if last else None

    def to_dict(self, include_stats=True):
        d = {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'address': self.address,
            'city': self.city,
            'country': self.country,
            'segment': self.segment,
            'rfm_score': self.rfm_score,
            'created_at': self.created_at.isoformat(),
        }
        if include_stats:
            d['total_orders']   = self.total_orders
            d['lifetime_value'] = round(self.lifetime_value, 2)
            d['last_order_date'] = self.last_order_date
        return d
