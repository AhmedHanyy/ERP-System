"""
Synthetic Data Seed Script
──────────────────────────
Generates realistic retail e-commerce data for SmartERP demo.

Data generated:
  - 8 product categories
  - 60 products with realistic pricing
  - 12 suppliers
  - 500 customers
  - 2000+ orders (18 months of history)
  - Realistic order patterns (seasonality, weekday effects)

NOTE: This is placeholder data.
When the real dataset arrives, replace this script with an ETL loader
that maps real data columns to the SmartERP schema defined in app/models/.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import random
import string
from datetime import datetime, timedelta
from faker import Faker
from app import create_app, db
from app.models import (
    Category, Product, Inventory, Customer,
    Order, OrderItem, Supplier, ProcurementRequest, InventoryLog
)

fake = Faker()
random.seed(42)
Faker.seed(42)

# ─── Product Catalog ──────────────────────────────────────────────────────────

CATEGORIES = [
    {'name': 'Electronics',    'icon': 'Cpu'},
    {'name': 'Clothing',       'icon': 'Shirt'},
    {'name': 'Home & Living',  'icon': 'Home'},
    {'name': 'Beauty',         'icon': 'Sparkles'},
    {'name': 'Sports',         'icon': 'Dumbbell'},
    {'name': 'Books',          'icon': 'BookOpen'},
    {'name': 'Toys',           'icon': 'Gamepad2'},
    {'name': 'Food & Drinks',  'icon': 'Coffee'},
]

PRODUCTS_TEMPLATE = [
    # Electronics
    {'name': 'Wireless Earbuds Pro',    'cat': 'Electronics', 'price': 1299, 'cost': 650},
    {'name': 'Smart Watch Series 5',    'cat': 'Electronics', 'price': 2499, 'cost': 1200},
    {'name': 'Bluetooth Speaker Mini',  'cat': 'Electronics', 'price': 599,  'cost': 280},
    {'name': 'USB-C Hub 7-Port',        'cat': 'Electronics', 'price': 349,  'cost': 140},
    {'name': 'Mechanical Keyboard RGB', 'cat': 'Electronics', 'price': 899,  'cost': 430},
    {'name': 'Webcam 4K HD',            'cat': 'Electronics', 'price': 749,  'cost': 350},
    {'name': 'Power Bank 20000mAh',     'cat': 'Electronics', 'price': 499,  'cost': 220},
    {'name': 'LED Ring Light Kit',      'cat': 'Electronics', 'price': 299,  'cost': 120},
    # Clothing
    {'name': 'Cotton Oversized Tee',    'cat': 'Clothing', 'price': 249, 'cost': 90},
    {'name': 'Slim Fit Chinos',         'cat': 'Clothing', 'price': 499, 'cost': 180},
    {'name': 'Hooded Sweatshirt',       'cat': 'Clothing', 'price': 599, 'cost': 220},
    {'name': 'Running Shorts',          'cat': 'Clothing', 'price': 199, 'cost': 70},
    {'name': 'Linen Summer Shirt',      'cat': 'Clothing', 'price': 399, 'cost': 140},
    {'name': 'Winter Puffer Jacket',    'cat': 'Clothing', 'price': 1299,'cost': 550},
    {'name': 'Classic White Sneakers',  'cat': 'Clothing', 'price': 799, 'cost': 350},
    # Home & Living
    {'name': 'Aromatherapy Diffuser',   'cat': 'Home & Living', 'price': 349, 'cost': 130},
    {'name': 'Bamboo Cutting Board Set','cat': 'Home & Living', 'price': 199, 'cost': 70},
    {'name': 'Ceramic Mug Set (4 pcs)', 'cat': 'Home & Living', 'price': 299, 'cost': 110},
    {'name': 'LED Fairy Lights 10m',    'cat': 'Home & Living', 'price': 149, 'cost': 55},
    {'name': 'Storage Ottoman Cube',    'cat': 'Home & Living', 'price': 599, 'cost': 260},
    {'name': 'Scented Candle Set',      'cat': 'Home & Living', 'price': 249, 'cost': 85},
    # Beauty
    {'name': 'Hyaluronic Acid Serum',   'cat': 'Beauty', 'price': 399, 'cost': 140},
    {'name': 'Vitamin C Face Cream',    'cat': 'Beauty', 'price': 349, 'cost': 120},
    {'name': 'Jade Roller Kit',         'cat': 'Beauty', 'price': 199, 'cost': 65},
    {'name': 'Eyebrow Shaping Kit',     'cat': 'Beauty', 'price': 149, 'cost': 50},
    {'name': 'Lip Gloss Bundle x5',     'cat': 'Beauty', 'price': 199, 'cost': 70},
    {'name': 'Natural Shampoo Bar',     'cat': 'Beauty', 'price': 89,  'cost': 28},
    # Sports
    {'name': 'Yoga Mat Anti-slip',      'cat': 'Sports', 'price': 299, 'cost': 110},
    {'name': 'Resistance Bands Set',    'cat': 'Sports', 'price': 199, 'cost': 70},
    {'name': 'Jump Rope Speed',         'cat': 'Sports', 'price': 149, 'cost': 48},
    {'name': 'Dumbbell Set 5kg Pair',   'cat': 'Sports', 'price': 699, 'cost': 300},
    {'name': 'Gym Gloves Pro',          'cat': 'Sports', 'price': 179, 'cost': 58},
    # Books
    {'name': 'Python for Data Science', 'cat': 'Books', 'price': 299, 'cost': 100},
    {'name': 'Atomic Habits',           'cat': 'Books', 'price': 199, 'cost': 65},
    {'name': 'Zero to One',             'cat': 'Books', 'price': 179, 'cost': 55},
    {'name': 'Deep Work',               'cat': 'Books', 'price': 189, 'cost': 60},
    # Toys
    {'name': 'STEM Building Blocks',    'cat': 'Toys', 'price': 399, 'cost': 160},
    {'name': 'Remote Control Car',      'cat': 'Toys', 'price': 599, 'cost': 250},
    {'name': 'Puzzle 1000 Pieces',      'cat': 'Toys', 'price': 199, 'cost': 70},
    # Food & Drinks
    {'name': 'Specialty Coffee Beans',  'cat': 'Food & Drinks', 'price': 349, 'cost': 140},
    {'name': 'Matcha Powder Premium',   'cat': 'Food & Drinks', 'price': 249, 'cost': 90},
    {'name': 'Protein Bar Box (12)',    'cat': 'Food & Drinks', 'price': 299, 'cost': 120},
    {'name': 'Herbal Tea Collection',   'cat': 'Food & Drinks', 'price': 199, 'cost': 72},
]

SUPPLIERS = [
    {'name': 'TechSource Egypt',        'contact': 'Ahmed Hassan',   'whatsapp': '+201012345678', 'rating': 4.5},
    {'name': 'FashionHub Cairo',        'contact': 'Sara Mohamed',   'whatsapp': '+201123456789', 'rating': 4.2},
    {'name': 'Home Essentials Co.',     'contact': 'Omar Karim',     'whatsapp': '+201234567890', 'rating': 4.0},
    {'name': 'Beauty World Imports',    'contact': 'Laila Nasser',   'whatsapp': '+201345678901', 'rating': 4.7},
    {'name': 'Sports Direct Wholesale', 'contact': 'Khaled Ali',     'whatsapp': '+201456789012', 'rating': 3.8},
    {'name': 'BookZone Distributors',   'contact': 'Nour Ibrahim',   'whatsapp': '+201567890123', 'rating': 4.3},
    {'name': 'KidsToys Egypt',          'contact': 'Yasmin Farouk',  'whatsapp': '+201678901234', 'rating': 3.9},
    {'name': 'FoodSource Premium',      'contact': 'Tarek Saad',     'whatsapp': '+201789012345', 'rating': 4.6},
    {'name': 'ElectroPlus MENA',        'contact': 'Heba Ramzy',     'whatsapp': '+201890123456', 'rating': 4.1},
    {'name': 'Smart Accessories Ltd',   'contact': 'Mohamed Fathy',  'whatsapp': '+201901234567', 'rating': 4.4},
    {'name': 'Global Garments Inc.',    'contact': 'Rana Elsyed',    'whatsapp': '+201012345670', 'rating': 3.7},
    {'name': 'Organic Foods Trading',   'contact': 'Amr Khalil',     'whatsapp': '+201123456780', 'rating': 4.8},
]

SEGMENTS = ['Champion', 'Loyal', 'At-Risk', 'Lost', 'New']
CITIES    = ['Cairo', 'Alexandria', 'Giza', 'Luxor', 'Aswan', 'Hurghada', 'Mansoura', 'Tanta', 'Suez', 'Ismailia']


def generate_sku(prefix, n):
    return f"{prefix}-{str(n).zfill(4)}"


def make_order_number(n):
    return f"ORD-{str(n).zfill(5)}"


def weighted_date(start_date, end_date):
    """Generate order dates with realistic patterns (more recent = more orders, weekday peaks)"""
    total_days = (end_date - start_date).days
    t = random.betavariate(2, 1)   # Skews toward recent dates
    base_date = start_date + timedelta(days=int(t * total_days))
    # Add slight weekday bias
    if base_date.weekday() >= 5:   # Weekend
        base_date += timedelta(days=random.choice([1, 2]))
    return base_date


def run_seed():
    app = create_app()
    with app.app_context():
        # Clear existing data
        db.drop_all()
        db.create_all()
        print("✓ Database schema created")

        # ── Categories ────────────────────────────────────────────────────────
        cat_map = {}
        for c in CATEGORIES:
            cat = Category(name=c['name'], icon=c['icon'])
            db.session.add(cat)
            db.session.flush()
            cat_map[c['name']] = cat.id
        print(f"✓ {len(CATEGORIES)} categories created")

        # ── Products + Inventory ──────────────────────────────────────────────
        product_objs = []
        for i, p in enumerate(PRODUCTS_TEMPLATE):
            prefix = ''.join([w[0] for w in p['cat'].split()[:2]]).upper()
            product = Product(
                name=p['name'],
                sku=generate_sku(prefix, i+1),
                category_id=cat_map[p['cat']],
                price=p['price'],
                cost=p['cost'],
                description=fake.sentence(nb_words=12),
                is_active=True,
            )
            db.session.add(product)
            db.session.flush()

            qty = random.randint(5, 150)
            inv = Inventory(
                product_id=product.id,
                quantity=qty,
                reorder_point=random.randint(10, 25),
                reorder_quantity=random.randint(30, 100),
                warehouse_location=f"W{random.randint(1,3)}-R{random.randint(1,10)}-S{random.randint(1,5)}",
                last_restocked=fake.date_time_between(start_date='-60d', end_date='now'),
            )
            db.session.add(inv)
            product_objs.append(product)

        print(f"✓ {len(PRODUCTS_TEMPLATE)} products + inventory records created")

        # ── Suppliers ─────────────────────────────────────────────────────────
        supplier_objs = []
        for s in SUPPLIERS:
            supplier = Supplier(
                name=s['name'],
                contact_person=s['contact'],
                email=fake.email(),
                phone=fake.phone_number(),
                whatsapp_number=s['whatsapp'],
                address=fake.address(),
                rating=s['rating'],
                lead_time_days=random.randint(3, 14),
                is_active=True,
            )
            db.session.add(supplier)
            supplier_objs.append(supplier)

        db.session.flush()
        print(f"✓ {len(SUPPLIERS)} suppliers created")

        # ── Customers ─────────────────────────────────────────────────────────
        customer_objs = []
        emails_used   = set()
        for _ in range(500):
            email = fake.email()
            while email in emails_used:
                email = fake.email()
            emails_used.add(email)

            c = Customer(
                name=fake.name(),
                email=email,
                phone=fake.phone_number(),
                address=fake.street_address(),
                city=random.choice(CITIES),
                country='Egypt',
                segment=random.choice(SEGMENTS),
                created_at=fake.date_time_between(start_date='-24m', end_date='-6m'),
            )
            db.session.add(c)
            customer_objs.append(c)

        db.session.flush()
        print(f"✓ {len(customer_objs)} customers created")

        # ── Orders ────────────────────────────────────────────────────────────
        start_date = datetime.utcnow() - timedelta(days=548)  # ~18 months
        end_date   = datetime.utcnow()
        statuses   = ['Pending', 'Preparing', 'Shipped', 'Delivered', 'Cancelled']
        status_weights = [0.05, 0.10, 0.15, 0.65, 0.05]

        order_count = 0
        for i in range(2200):
            customer  = random.choice(customer_objs)
            order_date = weighted_date(start_date, end_date)
            status    = random.choices(statuses, weights=status_weights)[0]
            num_items = random.choices([1, 2, 3, 4], weights=[0.5, 0.3, 0.15, 0.05])[0]
            chosen_products = random.sample(product_objs, min(num_items, len(product_objs)))

            order = Order(
                order_number=make_order_number(i + 1),
                customer_id=customer.id,
                status=status,
                discount=random.choice([0, 0, 0, 50, 100, 150]),
                shipping_fee=random.choice([0, 0, 29, 49]),
                notes=fake.sentence() if random.random() < 0.1 else None,
                created_at=order_date,
                updated_at=order_date + timedelta(hours=random.randint(1, 72)),
            )
            db.session.add(order)
            db.session.flush()

            total = 0
            for product in chosen_products:
                qty        = random.randint(1, 3)
                unit_price = product.price * random.uniform(0.95, 1.05)
                item = OrderItem(
                    order_id=order.id,
                    product_id=product.id,
                    quantity=qty,
                    unit_price=round(unit_price, 2),
                )
                db.session.add(item)
                total += qty * unit_price

            order.total_amount = round(total - order.discount + order.shipping_fee, 2)
            order_count += 1

        print(f"✓ {order_count} orders created (18 months of history)")

        # ── Procurement Requests ──────────────────────────────────────────────
        pr_statuses = ['Draft', 'Sent', 'Confirmed', 'Received', 'Cancelled']
        for _ in range(80):
            product  = random.choice(product_objs)
            supplier = random.choice(supplier_objs)
            qty      = random.randint(20, 100)
            status   = random.choice(pr_statuses)
            pr = ProcurementRequest(
                supplier_id=supplier.id,
                product_id=product.id,
                quantity=qty,
                unit_cost=product.cost,
                total_cost=round(product.cost * qty, 2),
                status=status,
                requested_at=fake.date_time_between(start_date='-12m', end_date='now'),
                expected_at=fake.date_time_between(start_date='-6m', end_date='+30d') if status != 'Draft' else None,
                received_at=fake.date_time_between(start_date='-9m', end_date='now') if status == 'Received' else None,
            )
            db.session.add(pr)

        print("✓ 80 procurement requests created")

        # ── Force low-stock on some products (for demo) ───────────────────────
        low_stock_products = random.sample(product_objs, 8)
        for p in low_stock_products:
            inv = Inventory.query.filter_by(product_id=p.id).first()
            if inv:
                inv.quantity = random.randint(0, inv.reorder_point - 1)

        print("✓ 8 products set to low/out-of-stock for demo")

        db.session.commit()
        print("\n✅ Seed complete! Database ready for SmartERP.")
        print("   Run: python run.py  →  Flask backend at http://localhost:5000")


if __name__ == '__main__':
    run_seed()
