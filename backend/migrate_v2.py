from app import create_app, db
from app.models import User, Product, Inventory, Customer, Order, Supplier
import os

app = create_app()

def migrate():
    with app.app_context():
        print("Initializing migration to Security v2 schema...")
        db.create_all()
        
        print("Seeding/updating default role-based users...")
        users_data = [
            ('admin', 'admin@smarterp.ai', 'Admin', 'admin'),
            ('ops', 'ops@smarterp.ai', 'Operations Manager', 'ops'),
            ('proc', 'proc@smarterp.ai', 'Procurement Officer', 'proc'),
            ('analytics', 'analytics@smarterp.ai', 'Analytics Manager', 'analytics'),
            ('cs', 'cs@smarterp.ai', 'Customer Service', 'cs'),
        ]
        for username, email, role, password in users_data:
            user = User.query.filter_by(username=username).first()
            if user:
                user.email = email
                user.role = role
                user.password = password
                user.status = 'Active'
                print(f"Updated user: {username}")
            else:
                user = User(username=username, email=email, role=role, password=password, status='Active')
                db.session.add(user)
                print(f"Created user: {username}")
        db.session.commit()
        print("Successfully seeded/updated users: admin, ops, proc, analytics, cs")

if __name__ == '__main__':
    migrate()
