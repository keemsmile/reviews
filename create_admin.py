from app import app, db
from models import User
from werkzeug.security import generate_password_hash

def create_platform_admin():
    with app.app_context():
        # Check if admin already exists
        admin = User.query.filter_by(email='admin@example.com').first()
        if admin:
            print("Admin user already exists!")
            return
        
        # Create new admin user
        admin = User(
            email='admin@example.com',
            password=generate_password_hash('admin123'),
            name='Platform Admin',
            role='platform_admin'
        )
        
        db.session.add(admin)
        db.session.commit()
        print("Platform admin created successfully!")
        print("Email: admin@example.com")
        print("Password: admin123")

if __name__ == '__main__':
    create_platform_admin()
