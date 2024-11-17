from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from models import db, Review, Business, User

admin = Blueprint('admin', __name__)

@admin.route('/admin/dashboard')
@login_required
def platform_dashboard():
    if current_user.role != 'platform_admin':
        flash('Access denied.')
        return redirect(url_for('main.index'))
    
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

@admin.route('/business/dashboard')
@login_required
def business_dashboard():
    if not current_user.business_id:
        flash('No business associated with this account.')
        return redirect(url_for('main.index'))
    
    # Get business-specific statistics
    business = Business.query.get(current_user.business_id)
    reviews = Review.query.filter_by(business_id=current_user.business_id)\
        .order_by(Review.created_at.desc()).all()
    
    total_reviews = len(reviews)
    avg_rating = sum(review.rating for review in reviews) / total_reviews if total_reviews > 0 else 0
    new_reviews = sum(1 for review in reviews if review.status == 'new')
    
    return render_template('admin/business_dashboard.html',
                         business=business,
                         reviews=reviews,
                         total_reviews=total_reviews,
                         avg_rating=round(avg_rating, 1),
                         new_reviews=new_reviews)

@admin.route('/business/reviews')
@login_required
def business_reviews():
    if not current_user.business_id:
        flash('No business associated with this account.')
        return redirect(url_for('main.index'))
    
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', 'all')
    rating_filter = request.args.get('rating', 'all')
    
    # Base query
    query = Review.query.filter_by(business_id=current_user.business_id)
    
    # Apply filters
    if status_filter != 'all':
        query = query.filter_by(status=status_filter)
    if rating_filter != 'all':
        query = query.filter_by(rating=int(rating_filter))
    
    # Order by date
    query = query.order_by(Review.created_at.desc())
    
    # Paginate
    reviews = query.paginate(page=page, per_page=10, error_out=False)
    
    return render_template('admin/reviews.html',
                         reviews=reviews,
                         status_filter=status_filter,
                         rating_filter=rating_filter)
