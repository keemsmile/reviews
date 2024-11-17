from app import app, db
from models import User, Business, Review
from werkzeug.security import generate_password_hash

def init_db():
    with app.app_context():
        # Drop all tables
        db.drop_all()
        
        # Create all tables
        db.create_all()
        
        # Create default business
        default_business = Business(
            name='Keem Smile Dentistry',
            branding_color='#007bff',
            logo_url=None
        )
        db.session.add(default_business)
        db.session.flush()  # This will populate the business.id
        
        # Create platform admin user
        platform_admin = User(
            email='admin@example.com',
            password=generate_password_hash('password123'),
            name='Platform Admin',
            role='platform_admin'
        )
        db.session.add(platform_admin)
        
        # Create business admin user
        business_admin = User(
            email='business@example.com',
            password=generate_password_hash('password123'),
            name='Business Admin',
            role='business_admin',
            business_id=default_business.id  # Link to the default business
        )
        db.session.add(business_admin)
        
        # Commit changes
        db.session.commit()
        print("Database initialized successfully!")
        print("\nTest Accounts:")
        print("1. Platform Admin:")
        print("   - Email: admin@example.com")
        print("   - Password: password123")
        print("2. Business Admin:")
        print("   - Email: business@example.com")
        print("   - Password: password123")

if __name__ == '__main__':
    init_db()
