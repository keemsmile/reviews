from app import app, db, client
from models import Business, Review, ReviewResponse, User
import json
from datetime import datetime
import logging
from sqlalchemy.exc import SQLAlchemyError

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_sentiment(review_data):
    """Get sentiment from stored review data."""
    return review_data.get('sentiment', 'neutral')

def extract_tags(text, rating):
    """Extract relevant tags from review text and rating."""
    tags = []
    
    # Add rating-based tags
    if rating >= 4:
        tags.append('positive')
    elif rating <= 2:
        tags.append('negative')
    else:
        tags.append('neutral')
    
    # Add common issue tags (can be expanded)
    lower_text = text.lower()
    if 'service' in lower_text:
        tags.append('service')
    if 'quality' in lower_text:
        tags.append('quality')
    if 'price' in lower_text or 'expensive' in lower_text or 'cost' in lower_text:
        tags.append('pricing')
    if 'wait' in lower_text or 'time' in lower_text:
        tags.append('timing')
    
    return tags

def get_or_create_business_admin(business_id):
    """Get or create a business admin for review responses."""
    admin = User.query.filter_by(
        business_id=business_id,
        role='business_admin'
    ).first()
    return admin.id if admin else None

def import_reviews(delete_existing=False):
    """Import reviews from reviews.json into the database."""
    try:
        with app.app_context():
            # Get the Keem Smile Dentistry business
            business = Business.query.filter_by(name="Keem Smile Dentistry").first()
            
            if not business:
                logger.error("Business 'Keem Smile Dentistry' not found!")
                return

            # Get business admin ID for responses
            admin_id = get_or_create_business_admin(business.id)

            # Optionally delete existing reviews
            if delete_existing:
                Review.query.filter_by(business_id=business.id).delete()
                db.session.commit()
                logger.info("Deleted existing reviews")

            # Load reviews from JSON
            try:
                with open('reviews.json', 'r') as f:
                    reviews_data = json.load(f)
            except FileNotFoundError:
                logger.error("reviews.json file not found!")
                return
            except json.JSONDecodeError:
                logger.error("Invalid JSON format in reviews.json!")
                return

            # Counters for statistics
            stats = {
                'imported': 0,
                'skipped': 0,
                'with_contact': 0,
                'with_improvement': 0,
                'with_responses': 0,
                'errors': 0,
                'total': len(reviews_data)
            }

            for review_data in reviews_data:
                try:
                    # Check if review already exists
                    existing_review = Review.query.filter_by(
                        business_id=business.id,
                        created_at=datetime.fromisoformat(review_data['timestamp'])
                    ).first()

                    if existing_review:
                        stats['skipped'] += 1
                        continue

                    # Process contact information
                    contact_info = {}
                    if review_data.get('contact_info'):
                        try:
                            if isinstance(review_data['contact_info'], str):
                                # Try to parse if it's a string
                                contact_info = json.loads(review_data['contact_info'])
                            else:
                                contact_info = review_data['contact_info']
                            stats['with_contact'] += 1
                        except json.JSONDecodeError:
                            contact_info = {}

                    # Create new review
                    review = Review(
                        business_id=business.id,
                        rating=review_data['rating'],
                        text=review_data['feedback'],
                        customer_name=contact_info.get('name', 'Anonymous'),
                        contact_info=contact_info,
                        created_at=datetime.fromisoformat(review_data['timestamp']),
                        last_updated=datetime.fromisoformat(review_data['timestamp']),
                        sentiment=get_sentiment(review_data),
                        source=review_data.get('source', 'website'),
                        improvement_feedback=review_data.get('improvement_feedback', ''),
                        tags=extract_tags(review_data['feedback'], review_data['rating']),
                        priority='high' if review_data['rating'] <= 2 else 'normal'
                    )

                    if review_data.get('improvement_feedback'):
                        stats['with_improvement'] += 1

                    db.session.add(review)
                    stats['imported'] += 1

                except Exception as e:
                    logger.error(f"Error processing review: {e}")
                    stats['errors'] += 1
                    continue

            # Commit all changes
            try:
                db.session.commit()
            except SQLAlchemyError as e:
                logger.error(f"Database error: {e}")
                db.session.rollback()
                return

            # Log statistics
            logger.info("\nImport completed!")
            logger.info(f"Successfully imported: {stats['imported']} reviews")
            logger.info(f"Skipped (already exist): {stats['skipped']} reviews")
            logger.info(f"Reviews with contact info: {stats['with_contact']}")
            logger.info(f"Reviews with improvement feedback: {stats['with_improvement']}")
            logger.info(f"Reviews with responses: {stats['with_responses']}")
            logger.info(f"Errors encountered: {stats['errors']}")
            logger.info(f"Total reviews processed: {stats['total']}")

    except Exception as e:
        logger.error(f"Import failed: {e}")

if __name__ == '__main__':
    import_reviews(delete_existing=True)
