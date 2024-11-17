from flask import Flask, render_template, request, redirect, url_for, jsonify, session
import os
from openai import OpenAI
import json
from datetime import datetime
from dotenv import load_dotenv
from functools import wraps
import time

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', os.urandom(24))

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Simple in-memory rate limiter
class RateLimiter:
    def __init__(self, max_requests=5, time_window=60):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = {}

    def is_allowed(self, ip):
        current_time = time.time()
        if ip not in self.requests:
            self.requests[ip] = []
        
        # Clean old requests
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

# Function to analyze sentiment using OpenAI
def analyze_sentiment(text):
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a sentiment analyzer. Respond with only 'positive' or 'negative'."},
                {"role": "user", "content": f"Analyze the sentiment of this text: {text}"}
            ]
        )
        sentiment = response.choices[0].message.content.strip().lower()
        return sentiment == 'positive'
    except Exception as e:
        print(f"Error in sentiment analysis: {e}")
        return False

# Function to store feedback (you can modify this to use your preferred storage method)
def store_feedback(feedback):
    try:
        with open('feedback.json', 'r') as f:
            feedbacks = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        feedbacks = []
    
    feedbacks.append(feedback)
    
    with open('feedback.json', 'w') as f:
        json.dump(feedbacks, f)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/submit_review', methods=['POST'])
@validate_review_data
def submit_review():
    data = request.get_json()
    rating = int(data.get('rating', 0))
    feedback = data.get('feedback', '').strip()
    # Run sentiment analysis on feedback
    is_positive = analyze_sentiment(feedback)

    # Store the review with sentiment
    review = {
        'rating': rating,
        'feedback': feedback,
        'sentiment': 'positive' if is_positive else 'negative',
        'timestamp': datetime.now().isoformat(),
        'contact_info': None  # Will be updated if user provides it later
    }
    
    try:
        with open('reviews.json', 'r') as f:
            reviews = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        reviews = []
    
    reviews.append(review)
    
    with open('reviews.json', 'w') as f:
        json.dump(reviews, f, indent=4)

    # Route based on rating AND sentiment
    if rating >= 4:  # Only 4 and 5 star reviews can potentially go to share
        if is_positive:
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
        feedback_data = request.get_json()
        improvement_feedback = feedback_data.get('feedback')
        improvement_areas = feedback_data.get('areas', [])
        initial_feedback = session.get('initial_feedback', '')
        
        # Find and update the most recent review for this feedback
        try:
            with open('reviews.json', 'r') as f:
                reviews = json.load(f)
            
            if reviews:
                # Update the most recent review with improvement feedback
                latest_review = reviews[-1]
                latest_review['improvement_feedback'] = improvement_feedback
                latest_review['improvement_areas'] = improvement_areas
                latest_review['needs_contact'] = None  # Will be updated in contact step
                
                with open('reviews.json', 'w') as f:
                    json.dump(reviews, f, indent=4)
        
        except (FileNotFoundError, json.JSONDecodeError):
            print("Error accessing reviews.json")
        
        return jsonify({'redirect': url_for('feedback_contact')})
    
    return render_template('feedback.html')

@app.route('/feedback/contact', methods=['GET', 'POST'])
def feedback_contact():
    if request.method == 'POST':
        data = request.get_json()
        
        try:
            with open('reviews.json', 'r') as f:
                reviews = json.load(f)
            
            if reviews:
                # Update the most recent review with contact preference
                latest_review = reviews[-1]
                
                if data.get('wantsContact'):
                    latest_review['needs_contact'] = True
                    latest_review['contact_info'] = {
                        'name': data.get('name'),
                        'contact': data.get('contactInfo'),
                        'preferred_method': data.get('preferredContact')
                    }
                else:
                    latest_review['needs_contact'] = False
                    latest_review['contact_info'] = None
                
                with open('reviews.json', 'w') as f:
                    json.dump(reviews, f, indent=4)
        
        except (FileNotFoundError, json.JSONDecodeError):
            print("Error accessing reviews.json")
        
        # Redirect based on contact preference
        if data.get('wantsContact'):
            return jsonify({'redirect': url_for('thank_you')})
        else:
            return jsonify({'redirect': url_for('goodbye')})
            
    return render_template('feedback_contact.html')

@app.route('/thank-you')
def thank_you():
    return render_template('thank_you.html')

@app.route('/goodbye')
def goodbye():
    return render_template('goodbye.html')

if __name__ == '__main__':
    app.run(debug=True)
