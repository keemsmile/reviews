from flask import Flask, render_template, request, redirect, url_for, jsonify, session
import os
from datetime import datetime
from dotenv import load_dotenv
from functools import wraps
import time
from flask_login import LoginManager, current_user
from models import db, User, Business, Review
from auth import auth as auth_blueprint
from admin import admin as admin_blueprint
import openai

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', os.urandom(24))

# Initialize OpenAI client
openai.api_key = os.getenv('OPENAI_API_KEY')

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

# Rate limiting for OpenAI API
OPENAI_RATE_LIMIT = {}
MAX_REQUESTS_PER_MINUTE = 50  # Adjust based on your OpenAI plan
RATE_LIMIT_WINDOW = 60  # seconds

def check_rate_limit():
    """Check if we're within OpenAI API rate limits."""
    current_time = time.time()
    # Clean up old entries
    for timestamp in list(OPENAI_RATE_LIMIT.keys()):
        if current_time - timestamp > RATE_LIMIT_WINDOW:
            del OPENAI_RATE_LIMIT[timestamp]
    
    # Check if we're within limits
    if len(OPENAI_RATE_LIMIT) >= MAX_REQUESTS_PER_MINUTE:
        return False
    
    # Add current request
    OPENAI_RATE_LIMIT[current_time] = True
    return True

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
    """Determine sentiment using OpenAI, with robust error handling and rate limiting."""
    if not os.getenv('OPENAI_API_KEY'):
        print("ERROR: OpenAI API key not found!")
        raise ValueError("OpenAI API key is required for sentiment analysis")

    if not check_rate_limit():
        print("WARNING: OpenAI API rate limit reached, waiting...")
        time.sleep(5)  # Wait 5 seconds before retrying
        if not check_rate_limit():
            raise Exception("Rate limit exceeded, please try again later")

    try:
        max_retries = 3
        retry_delay = 2  # seconds
        
        for attempt in range(max_retries):
            try:
                response = openai.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a sentiment analysis expert. Analyze the following review and respond with ONLY one word: 'positive', 'neutral', or 'negative'."
                        },
                        {
                            "role": "user",
                            "content": feedback
                        }
                    ],
                    temperature=0,
                    max_tokens=1,
                    timeout=10  # 10 second timeout
                )
                
                sentiment = response.choices[0].message.content.strip().lower()
                
                # Validate sentiment value
                if sentiment not in ['positive', 'negative', 'neutral']:
                    print(f"WARNING: Invalid sentiment '{sentiment}' from OpenAI, retrying...")
                    raise ValueError("Invalid sentiment value")
                
                return sentiment
                
            except openai.RateLimitError:
                print(f"WARNING: OpenAI rate limit hit, attempt {attempt + 1}/{max_retries}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (attempt + 1))  # Exponential backoff
                else:
                    raise
                    
            except openai.APITimeoutError:
                print(f"WARNING: OpenAI API timeout, attempt {attempt + 1}/{max_retries}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                else:
                    raise
                    
            except ValueError as e:
                print(f"WARNING: OpenAI returned invalid data, attempt {attempt + 1}/{max_retries}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                else:
                    raise
                
    except Exception as e:
        print(f"ERROR in OpenAI sentiment analysis: {str(e)}")
        # Log the error with full context
        error_context = {
            'error_type': type(e).__name__,
            'error_message': str(e),
            'rating': rating,
            'feedback_length': len(feedback),
            'timestamp': datetime.now().isoformat()
        }
        print(f"Error context: {error_context}")
        
        # Fallback to rating-based sentiment only if API completely fails
        if rating >= 4:
            return 'positive'
        elif rating <= 2:
            return 'negative'
        return 'neutral'

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
    
    # Get sentiment from OpenAI
    sentiment = determine_sentiment(rating, feedback)

    try:
        # Save directly to database
        business = Business.query.first()
        if business:
            db_review = Review(
                rating=rating,
                text=feedback,
                sentiment=sentiment,
                business_id=business.id,
                created_at=datetime.now(),
                status='new',
                priority='high' if rating <= 2 else 'normal'
            )
            db.session.add(db_review)
            db.session.commit()
    except Exception as e:
        print(f"Error saving to database: {e}")
        return jsonify({'error': 'Failed to save review'}), 500

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
            # Update the last review with improvement feedback
            business = Business.query.first()
            if business:
                db_review = Review.query.filter_by(business_id=business.id).order_by(Review.created_at.desc()).first()
                if db_review:
                    db_review.improvement_feedback = feedback
                    db_review.improvement_areas = improvement_areas
                    db.session.commit()
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
            # Update the last review with contact information
            business = Business.query.first()
            if business:
                db_review = Review.query.filter_by(business_id=business.id).order_by(Review.created_at.desc()).first()
                if db_review:
                    db_review.contact_info = contact_info
                    db.session.commit()
                
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

def initialize_app():
    """Initialize the application."""
    with app.app_context():
        db.create_all()

if __name__ == '__main__':
    initialize_app()
    app.run(debug=True)
