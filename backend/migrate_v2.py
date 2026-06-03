from app import create_app, db
from app.models import User, Product, Inventory, Customer, Order, Supplier
import os

app = create_app()

def migrate():
    with app.app_context():
        print("Initializing migration to Security v2 schema...")
        db.create_all()
        
        # Check if Admin exists, if not create default users
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            print("Seeding default role-based users...")
            users = [
                User(username='admin', email='admin@smarterp.ai', role='Admin', password='admin'),
                User(username='ops', email='ops@smarterp.ai', role='Operations Manager', password='ops'),
                User(username='proc', email='proc@smarterp.ai', role='Procurement Staff', password='proc'),
                User(username='analytics', email='data@smarterp.ai', role='Analytics Manager', password='data'),
                User(username='cs', email='cs@smarterp.ai', role='Customer Service', password='cs'),
            ]
            for u in users:
                db.session.add(u)
            
            db.session.commit()
            print("Successfully seeded users: admin, ops, proc, analytics, cs")
        else:
            print("Users already exist. Skipping seed.")

if __name__ == '__main__':
    migrate()
