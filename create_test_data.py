from app import app, db
from models import User, Business, Review, ReviewResponse
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta
import random

def create_test_data():
    with app.app_context():
        # Create a test business
        business = Business(
            name="Keem Smile Dentistry",
            branding_color="#007bff",
            logo_url="/static/images/logo.png",
            is_active=True
        )
        db.session.add(business)
        db.session.flush()  # To get the business ID

        # Create a business admin
        business_admin = User(
            email="dentist@keemsmile.com",
            password=generate_password_hash("dental123"),
            name="Dr. Keem",
            role="business_admin",
            business_id=business.id
        )
        db.session.add(business_admin)
        db.session.flush()  # Get the business admin ID

        # Create sample reviews
        review_texts = [
            "Great experience! Dr. Keem was very professional and gentle.",
            "The staff was friendly and the office is modern and clean.",
            "Best dental experience I've ever had. Highly recommend!",
            "Very thorough cleaning and examination. Will definitely return.",
            "The team made me feel comfortable throughout my visit.",
            "State-of-the-art equipment and excellent care.",
            "Dr. Keem explained everything clearly. Very satisfied!",
            "Quick appointment scheduling and no waiting time.",
            "Fantastic service and very reasonable prices.",
            "My kids love coming here! Very family-friendly practice."
        ]

        customer_names = [
            "John Smith", "Sarah Johnson", "Michael Brown", "Emily Davis",
            "David Wilson", "Lisa Anderson", "Robert Taylor", "Jennifer Martin",
            "William Thompson", "Jessica White"
        ]

        # Create reviews with different dates and statuses
        for i in range(10):
            days_ago = random.randint(0, 30)
            review_date = datetime.utcnow() - timedelta(days=days_ago)
            status = random.choice(['new', 'read', 'responded'])
            rating = random.randint(4, 5)  # Mostly positive reviews

            review = Review(
                rating=rating,
                text=review_texts[i],
                customer_name=customer_names[i],
                status=status,
                created_at=review_date,
                business_id=business.id
            )
            db.session.add(review)
            db.session.flush()  # Get the review ID

            # Add responses to some reviews
            if status == 'responded':
                response = ReviewResponse(
                    text=f"Thank you for your feedback, {customer_names[i].split()[0]}! We're glad you had a great experience.",
                    review_id=review.id,
                    responder_id=business_admin.id,
                    created_at=review_date + timedelta(days=1)
                )
                db.session.add(response)

        db.session.commit()
        print("Test data created successfully!")
        print("\nBusiness Admin Login:")
        print("Email: dentist@keemsmile.com")
        print("Password: dental123")

if __name__ == '__main__':
    create_test_data()
