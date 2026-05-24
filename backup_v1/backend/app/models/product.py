from app import db
from datetime import datetime


class Category(db.Model):
    """
    Product categories (hierarchical - supports parent/child).
    NOTE: When real dataset arrives, adjust category names and hierarchy to match real taxonomy.
    """
    __tablename__ = 'categories'
    id         = db.Column(db.Integer, primary_key=True)
    name       = db.Column(db.String(100), nullable=False)
    parent_id  = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    icon       = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    products   = db.relationship('Product', back_populates='category', lazy='dynamic')
    children   = db.relationship('Category', backref=db.backref('parent', remote_side=[id]))

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'parent_id': self.parent_id,
            'icon': self.icon,
            'product_count': self.products.count(),
        }


class Product(db.Model):
    """
    Core product catalog.
    NOTE: When real dataset arrives, SKU format, variant handling, and cost structure may change.
    """
    __tablename__ = 'products'
    id          = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.String(200), nullable=False)
    sku         = db.Column(db.String(50), unique=True, nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    price       = db.Column(db.Float, nullable=False)   # Selling price
    cost        = db.Column(db.Float, nullable=False)   # Purchase/COGS cost
    description = db.Column(db.Text, nullable=True)
    image_url   = db.Column(db.String(300), nullable=True)
    is_active   = db.Column(db.Boolean, default=True)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

    category    = db.relationship('Category', back_populates='products')
    inventory   = db.relationship('Inventory', back_populates='product', uselist=False)
    order_items = db.relationship('OrderItem', back_populates='product', lazy='dynamic')

    @property
    def margin(self):
        if self.price > 0:
            return round(((self.price - self.cost) / self.price) * 100, 2)
        return 0

    def to_dict(self, include_inventory=True):
        d = {
            'id': self.id,
            'name': self.name,
            'sku': self.sku,
            'category_id': self.category_id,
            'category_name': self.category.name if self.category else None,
            'price': self.price,
            'cost': self.cost,
            'margin': self.margin,
            'description': self.description,
            'image_url': self.image_url,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat(),
        }
        if include_inventory and self.inventory:
            d['inventory'] = self.inventory.to_dict()
        return d
