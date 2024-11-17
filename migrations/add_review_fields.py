import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db
from models import Review
from sqlalchemy import text
from datetime import datetime

def upgrade():
    """Add new columns to the review table."""
    with app.app_context():
        # Add last_updated column with a fixed timestamp
        try:
            current_time = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
            db.session.execute(text(f'ALTER TABLE review ADD COLUMN last_updated DATETIME DEFAULT "{current_time}"'))
            print("Added last_updated column")
        except Exception as e:
            print(f"Error adding last_updated column: {e}")

        # Update last_updated for existing rows
        try:
            db.session.execute(text('UPDATE review SET last_updated = created_at'))
            print("Updated last_updated values")
        except Exception as e:
            print(f"Error updating last_updated values: {e}")

        # Add other columns
        try:
            db.session.execute(text('ALTER TABLE review ADD COLUMN sentiment VARCHAR(20)'))
            print("Added sentiment column")
        except Exception as e:
            print(f"Error adding sentiment column: {e}")

        try:
            db.session.execute(text('ALTER TABLE review ADD COLUMN source VARCHAR(50)'))
            print("Added source column")
        except Exception as e:
            print(f"Error adding source column: {e}")

        try:
            db.session.execute(text('ALTER TABLE review ADD COLUMN contact_info JSON'))
            print("Added contact_info column")
        except Exception as e:
            print(f"Error adding contact_info column: {e}")

        try:
            db.session.execute(text('ALTER TABLE review ADD COLUMN improvement_feedback TEXT'))
            print("Added improvement_feedback column")
        except Exception as e:
            print(f"Error adding improvement_feedback column: {e}")

        try:
            db.session.execute(text('ALTER TABLE review ADD COLUMN tags JSON'))
            print("Added tags column")
        except Exception as e:
            print(f"Error adding tags column: {e}")

        try:
            db.session.execute(text('ALTER TABLE review ADD COLUMN priority VARCHAR(20) DEFAULT "normal"'))
            print("Added priority column")
        except Exception as e:
            print(f"Error adding priority column: {e}")

        db.session.commit()
        print("Migration completed successfully!")

def downgrade():
    """Remove added columns from the review table."""
    with app.app_context():
        columns = [
            'last_updated',
            'sentiment',
            'source',
            'contact_info',
            'improvement_feedback',
            'tags',
            'priority'
        ]
        
        for column in columns:
            try:
                db.session.execute(text(f'ALTER TABLE review DROP COLUMN {column}'))
                print(f"Dropped {column} column")
            except Exception as e:
                print(f"Error dropping {column} column: {e}")
        
        db.session.commit()
        print("Downgrade completed successfully!")

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'downgrade':
        downgrade()
    else:
        upgrade()
