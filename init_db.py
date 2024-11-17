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
        
        # Create admin user
        admin = User(
            email='admin@example.com',
            password=generate_password_hash('password123'),
            name='Admin User',
            role='platform_admin'
        )
        db.session.add(admin)
        
        # Commit changes
        db.session.commit()

if __name__ == '__main__':
    init_db()
    print("Database initialized successfully!")
