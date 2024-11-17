from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from models import db, Review, Business, User
from collections import Counter
from sqlalchemy import func
from datetime import datetime

admin = Blueprint('admin', __name__)

@admin.route('/dashboard')
@login_required
def platform_dashboard():
    if current_user.role != 'platform_admin':
        flash('Access denied.')
        return redirect(url_for('index'))
    
    # Get platform-wide statistics
    total_businesses = Business.query.count()
    total_reviews = Review.query.count()
    total_users = User.query.count()
    
    businesses = Business.query.order_by(Business.created_at.desc()).all()
    
    return render_template('admin/platform_dashboard.html',
                         total_businesses=total_businesses,
                         total_reviews=total_reviews,
                         total_users=total_users,
                         businesses=businesses)

@admin.route('/business-dashboard')
@login_required
def business_dashboard():
    if current_user.role != 'business_admin':
        flash('Access denied. Business admin only.')
        return redirect(url_for('index'))
    
    if not current_user.business_id:
        flash('No business associated with this account.')
        return redirect(url_for('index'))
    
    # Get business-specific statistics
    business = Business.query.get(current_user.business_id)
    if not business:
        flash('Business not found.')
        return redirect(url_for('index'))

    reviews = Review.query.filter_by(business_id=current_user.business_id)\
        .order_by(Review.created_at.desc()).all()
    
    total_reviews = len(reviews)
    
    # Initialize default values
    avg_rating = 0
    new_reviews = 0
    urgent_reviews = 0
    sentiment_counts = {'positive': 0, 'neutral': 0, 'negative': 0}
    common_tags = []
    rating_distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    source_stats = []

    if total_reviews > 0:
        # Calculate statistics
        avg_rating = sum(review.rating for review in reviews) / total_reviews
        new_reviews = sum(1 for review in reviews if review.status == 'new')
        urgent_reviews = sum(1 for review in reviews if review.priority == 'urgent')
        
        # Calculate sentiment distribution
        sentiment_counts = {
            'positive': sum(1 for r in reviews if r.sentiment == 'positive'),
            'neutral': sum(1 for r in reviews if r.sentiment == 'neutral'),
            'negative': sum(1 for r in reviews if r.sentiment == 'negative')
        }
        
        # Calculate tag distribution
        all_tags = []
        for review in reviews:
            if review.tags:
                all_tags.extend(review.tags)
        common_tags = Counter(all_tags).most_common(10)
        
        # Calculate rating distribution
        rating_distribution = Counter(review.rating for review in reviews)
        
        # Calculate source statistics
        sources = set(review.source for review in reviews if review.source)
        for source in sources:
            source_reviews = [r for r in reviews if r.source == source]
            source_stats.append({
                'name': source,
                'count': len(source_reviews),
                'avg_rating': sum(r.rating for r in source_reviews) / len(source_reviews)
            })
        source_stats.sort(key=lambda x: x['count'], reverse=True)
    
    return render_template('admin/business_dashboard.html',
                         business=business,
                         reviews=reviews,  # Show all reviews for modal functionality
                         total_reviews=total_reviews,
                         avg_rating=round(avg_rating, 1),
                         new_reviews=new_reviews,
                         urgent_reviews=urgent_reviews,
                         sentiment_counts=sentiment_counts,
                         common_tags=common_tags,
                         rating_distribution=rating_distribution,
                         source_stats=source_stats)

@admin.route('/business-reviews')
@login_required
def business_reviews():
    if current_user.role != 'business_admin':
        flash('Access denied. Business admin only.')
        return redirect(url_for('index'))

    if not current_user.business_id:
        flash('No business associated with this account.')
        return redirect(url_for('index'))
    
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    reviews = Review.query.filter_by(business_id=current_user.business_id)\
        .order_by(Review.created_at.desc())\
        .paginate(page=page, per_page=per_page)
    
    return render_template('admin/reviews.html',
                         reviews=reviews)

@admin.route('/respond-to-review/<int:review_id>', methods=['POST'])
@login_required
def respond_to_review(review_id):
    if current_user.role != 'business_admin':
        flash('Access denied. Business admin only.')
        return redirect(url_for('index'))
    
    review = Review.query.get_or_404(review_id)
    
    # Verify the review belongs to the admin's business
    if review.business_id != current_user.business_id:
        flash('Access denied. This review does not belong to your business.')
        return redirect(url_for('admin.business_dashboard'))
    
    response = request.form.get('response', '').strip()
    if not response:
        flash('Response cannot be empty.')
        return redirect(url_for('admin.business_dashboard'))
    
    # Update review with response
    review.response = response
    review.status = 'responded'
    review.response_date = datetime.utcnow()
    review.responded_by_id = current_user.id
    
    try:
        db.session.commit()
        flash('Response submitted successfully.')
    except Exception as e:
        db.session.rollback()
        flash('Error submitting response. Please try again.')
        print(f"Error submitting response: {e}")
    
    return redirect(url_for('admin.business_dashboard'))
