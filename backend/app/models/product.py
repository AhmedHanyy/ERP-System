from app import db
from datetime import datetime


class Category(db.Model):
    """
    Product categories (hierarchical - supports parent/child).
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
    Core product catalog with lifecycle informatics.
    """
    __tablename__ = 'products'
    id          = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.String(200), nullable=False)
    sku         = db.Column(db.String(50), unique=True, nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    price       = db.Column(db.Float, nullable=False)   # Base Selling price
    cost        = db.Column(db.Float, nullable=False)   # Base Purchase cost
    description = db.Column(db.Text, nullable=True)
    image_url   = db.Column(db.String(300), nullable=True)
    is_active   = db.Column(db.Boolean, default=True)
    lifecycle_stage = db.Column(db.String(50), default='Growth') # Introduction, Growth, Maturity, Decline
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

    category    = db.relationship('Category', back_populates='products')
    inventory   = db.relationship('Inventory', back_populates='product', uselist=False)
    variants    = db.relationship('ProductVariant', back_populates='product', cascade='all, delete-orphan')
    order_items = db.relationship('OrderItem', back_populates='product', lazy='dynamic')

    @property
    def margin(self):
        if self.price > 0:
            return round(((self.price - self.cost) / self.price) * 100, 2)
        return 0

    def to_dict(self, include_inventory=True, include_variants=True):
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
            'lifecycle_stage': self.lifecycle_stage,
            'created_at': self.created_at.isoformat(),
        }
        if include_variants:
            d['variants'] = [v.to_dict() for v in self.variants]
        if include_inventory and self.inventory:
            d['inventory'] = self.inventory.to_dict()
        return d


class ProductVariant(db.Model):
    """
    Sub-products for size, color, or material variations.
    """
    __tablename__ = 'product_variants'
    id         = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    name       = db.Column(db.String(100), nullable=False) # e.g. "XL", "Navy Blue"
    type       = db.Column(db.String(50), nullable=False) # e.g. "Size", "Color"
    sku_suffix = db.Column(db.String(20), nullable=False)
    price_adj  = db.Column(db.Float, default=0.0) # Price adjustment relative to base product
    stock      = db.Column(db.Integer, default=0)

    product    = db.relationship('Product', back_populates='variants')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'type': self.type,
            'sku_suffix': self.sku_suffix,
            'price_adj': self.price_adj,
            'stock': self.stock
        }
