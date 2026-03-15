import random
from datetime import datetime, timedelta, timezone
from app import app, db, User, Book, Transaction
from werkzeug.security import generate_password_hash

def generate_history():
    with app.app_context():
        print("-> Generating fake historical users...")
        # Create 10 dummy users
        users = []
        for i in range(1, 11):
            username = f'student_{i}'
            # Check if user exists
            user = User.query.filter_by(username=username).first()
            if not user:
                user = User(username=username, password=generate_password_hash('password123'))
                db.session.add(user)
                db.session.commit()
            users.append(user)
            
        print("-> Finding 10 books to make 'trending'...")
        books = Book.query.limit(50).all()
        # Pick 10 books to have lots of fake transactions
        trending_books = random.sample(books, 10)
        
        now = datetime.now(timezone.utc)
        print("-> Creating 300 fake transactions over the last 30 days...")
        
        for _ in range(300):
            # 70% chance to borrow a "trending" book, 30% chance for random
            if random.random() < 0.7:
                book = random.choice(trending_books)
            else:
                book = random.choice(books)
                
            user = random.choice(users)
            
            # Random issue date within last 30 days
            days_ago = random.randint(1, 30)
            issue_date = now - timedelta(days=days_ago)
            
            # Most books are returned 2-5 days later
            is_returned = random.random() < 0.8  # 80% of books are returned
            
            if is_returned:
                borrow_duration = random.randint(2, 5)
                return_date = issue_date + timedelta(days=borrow_duration)
                if return_date > now:
                     return_date = now # Cap return dates
            else:
                 return_date = None
                 
            txn = Transaction(
                 book_id=book.id,
                 user_id=user.id,
                 issue_date=issue_date,
                 return_date=return_date
            )
            db.session.add(txn)
            
        db.session.commit()
        print("✅ Success! Generated simulated history.")

if __name__ == '__main__':
    generate_history()
