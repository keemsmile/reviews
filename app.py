from flask import Flask, render_template, request, redirect, url_for, jsonify, session
import os
import json
from datetime import datetime
from dotenv import load_dotenv
from functools import wraps
import time
from flask_login import LoginManager, current_user
from models import db, User, Business, Review
from auth import auth as auth_blueprint
from admin import admin as admin_blueprint

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', os.urandom(24))

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///reviews.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Register blueprints
app.register_blueprint(auth_blueprint, url_prefix='/auth')
app.register_blueprint(admin_blueprint, url_prefix='/admin')

# Simple in-memory rate limiter with cleanup
class RateLimiter:
    def __init__(self, max_requests=5, time_window=60):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = {}
        self.last_cleanup = time.time()
        self.cleanup_interval = 300  # Cleanup every 5 minutes

    def cleanup_old_requests(self):
        """Remove old requests from memory"""
        current_time = time.time()
        if current_time - self.last_cleanup > self.cleanup_interval:
            cutoff_time = current_time - self.time_window
            self.requests = {
                ip: [t for t in times if t > cutoff_time]
                for ip, times in self.requests.items()
            }
            # Remove empty IP entries
            self.requests = {
                ip: times for ip, times in self.requests.items()
                if times
            }
            self.last_cleanup = current_time

    def is_allowed(self, ip):
        current_time = time.time()
        self.cleanup_old_requests()
        
        if ip not in self.requests:
            self.requests[ip] = []
        
        # Clean old requests for this IP
        self.requests[ip] = [req_time for req_time in self.requests[ip] 
                           if current_time - req_time < self.time_window]
        
        if len(self.requests[ip]) >= self.max_requests:
            return False
        
        self.requests[ip].append(current_time)
        return True

rate_limiter = RateLimiter()

def validate_review_data(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.method == 'POST':
            data = request.get_json()
            
            # Validate rating
            rating = data.get('rating')
            if not isinstance(rating, int) or not (1 <= rating <= 5):
                return jsonify({'error': 'Invalid rating value'}), 400
            
            # Validate feedback text
            feedback = data.get('feedback', '').strip()
            if not feedback or len(feedback) > 1000:  # Max 1000 chars
                return jsonify({'error': 'Invalid feedback length'}), 400
            
            # Check for potential XSS/injection
            dangerous_patterns = ['<script>', 'javascript:', 'onload=', 'onerror=']
            if any(pattern in feedback.lower() for pattern in dangerous_patterns):
                return jsonify({'error': 'Invalid feedback content'}), 400
            
            # Rate limiting
            if not rate_limiter.is_allowed(request.remote_addr):
                return jsonify({'error': 'Too many requests. Please try again later.'}), 429
        
        return f(*args, **kwargs)
    return decorated_function

def determine_sentiment(rating, feedback):
    """Determine sentiment based on rating and feedback content."""
    # Base sentiment on rating
    if rating >= 4:
        base_sentiment = 'positive'
    elif rating <= 2:
        base_sentiment = 'negative'
    else:
        base_sentiment = 'neutral'
    
    # Adjust based on feedback content
    negative_words = {'bad', 'terrible', 'awful', 'horrible', 'worst', 'poor', 'disappointed', 'never', 'waste'}
    positive_words = {'good', 'great', 'excellent', 'amazing', 'wonderful', 'best', 'love', 'perfect', 'recommend'}
    
    feedback_lower = feedback.lower()
    neg_count = sum(1 for word in negative_words if word in feedback_lower)
    pos_count = sum(1 for word in positive_words if word in feedback_lower)
    
    # Adjust sentiment if feedback strongly contradicts rating
    if base_sentiment == 'positive' and neg_count > pos_count + 2:
        return 'negative'
    elif base_sentiment == 'negative' and pos_count > neg_count + 2:
        return 'positive'
    
    return base_sentiment

def sync_json_to_db():
    """Sync reviews from JSON file to database."""
    try:
        # Get the first business (for now)
        business = Business.query.first()
        if not business:
            print("No business found in database")
            return

        # Load JSON reviews
        with open('reviews.json', 'r') as f:
            json_reviews = json.load(f)

        # Get existing review texts to avoid duplicates
        existing_reviews = set(r.text for r in Review.query.all())

        # Add new reviews to database
        for review_data in json_reviews:
            if review_data['feedback'] not in existing_reviews:
                try:
                    timestamp = datetime.fromisoformat(review_data['timestamp'])
                except ValueError:
                    timestamp = datetime.now()

                db_review = Review(
                    rating=review_data['rating'],
                    text=review_data['feedback'],
                    sentiment=review_data['sentiment'],
                    business_id=business.id,
                    created_at=timestamp,
                    status='new',
                    priority='normal' if review_data['rating'] >= 3 else 'high'
                )
                db.session.add(db_review)
                existing_reviews.add(review_data['feedback'])

        db.session.commit()
        print(f"Successfully synced reviews to database")
    except Exception as e:
        print(f"Error syncing reviews: {e}")
        db.session.rollback()

def initialize_app():
    """Initialize the application."""
    # Create all database tables
    db.create_all()
    
    # Create a default business if none exists
    if not Business.query.first():
        default_business = Business(
            name="Keem Smile Dentistry",
            is_active=True
        )
        db.session.add(default_business)
        db.session.commit()
    
    # Sync reviews from JSON to database
    sync_json_to_db()

# Initialize the app when it starts
with app.app_context():
    initialize_app()

@app.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.role == 'platform_admin':
            return redirect(url_for('admin.platform_dashboard'))
        return redirect(url_for('admin.business_dashboard'))
    return render_template('index.html')

@app.route('/submit_review', methods=['POST'])
@validate_review_data
def submit_review():
    data = request.get_json()
    rating = int(data.get('rating', 0))
    feedback = data.get('feedback', '').strip()
    
    # Determine sentiment without API call
    sentiment = determine_sentiment(rating, feedback)

    # Store the review with sentiment
    review_data = {
        'rating': rating,
        'feedback': feedback,
        'sentiment': sentiment,
        'timestamp': datetime.now().isoformat(),
        'contact_info': None  # Will be updated if user provides it later
    }
    
    # Save to JSON file
    try:
        with open('reviews.json', 'r') as f:
            reviews = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        reviews = []
    
    reviews.append(review_data)
    
    with open('reviews.json', 'w') as f:
        json.dump(reviews, f, indent=4)

    # Save to database
    try:
        # For now, assign to the first business in the database
        business = Business.query.first()
        if business:
            db_review = Review(
                rating=rating,
                text=feedback,
                sentiment=sentiment,
                business_id=business.id,
                created_at=datetime.now(),
                status='new',
                priority='normal' if rating >= 3 else 'high'
            )
            db.session.add(db_review)
            db.session.commit()
    except Exception as e:
        print(f"Error saving to database: {e}")
        # Don't stop the flow if database save fails
        pass

    # Route based on rating AND sentiment
    if rating >= 4:  # Only 4 and 5 star reviews can potentially go to share
        if sentiment == 'positive':
            return jsonify({
                'redirect': url_for('share')
            })
        else:
            # Even high-star reviews with negative sentiment go to feedback
            session['initial_feedback'] = feedback
            return jsonify({
                'redirect': url_for('feedback')
            })
    else:
        # For 3 stars or lower, always go to feedback regardless of sentiment
        session['initial_feedback'] = feedback
        return jsonify({
            'redirect': url_for('feedback')
        })

@app.route('/share')
def share():
    return render_template('share.html')

@app.route('/thanks')
def thanks():
    return render_template('thanks.html')

@app.route('/feedback', methods=['GET', 'POST'])
def feedback():
    if request.method == 'POST':
        data = request.get_json()
        feedback = data.get('feedback', '').strip()
        improvement_areas = data.get('areas', [])
        
        try:
            with open('reviews.json', 'r') as f:
                reviews = json.load(f)
            
            # Update the last review with improvement feedback
            if reviews:
                reviews[-1]['improvement_feedback'] = feedback
                reviews[-1]['improvement_areas'] = improvement_areas
                
                with open('reviews.json', 'w') as f:
                    json.dump(reviews, f, indent=4)
        except Exception as e:
            print(f"Error storing feedback: {e}")
        
        return jsonify({
            'redirect': url_for('feedback_contact')
        })
    
    return render_template('feedback.html', 
                         initial_feedback=session.get('initial_feedback', ''))

@app.route('/feedback/contact', methods=['GET', 'POST'])
def feedback_contact():
    if request.method == 'POST':
        data = request.get_json()
        contact_info = {
            'name': data.get('name', '').strip(),
            'email': data.get('email', '').strip(),
            'phone': data.get('phone', '').strip(),
            'preferred_contact': data.get('preferred_contact', 'email')
        }
        
        try:
            with open('reviews.json', 'r') as f:
                reviews = json.load(f)
            
            # Update the last review with contact information
            if reviews:
                reviews[-1]['contact_info'] = contact_info
                
                with open('reviews.json', 'w') as f:
                    json.dump(reviews, f, indent=4)
                
                return jsonify({
                    'redirect': url_for('thank_you')
                })
        except Exception as e:
            print(f"Error storing contact info: {e}")
            return jsonify({
                'error': 'Failed to store contact information'
            }), 500
    
    return render_template('feedback_contact.html')

@app.route('/thank-you')
def thank_you():
    return render_template('thank_you.html')

@app.route('/goodbye')
def goodbye():
    return render_template('goodbye.html')

if __name__ == '__main__':
    app.run(debug=True)
