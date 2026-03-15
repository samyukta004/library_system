from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime, timezone, timedelta
from sqlalchemy import func

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///library.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Login Management Configuration
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

# --- DATABASE MODELS ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)

class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    author = db.Column(db.String(100), nullable=False)
    total_stock = db.Column(db.Integer, default=1)
    available_stock = db.Column(db.Integer, default=1)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    issue_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    return_date = db.Column(db.DateTime, nullable=True)
    
    book = db.relationship('Book', backref=db.backref('transactions', lazy=True))
    user = db.relationship('User', backref=db.backref('transactions', lazy=True))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- AUTH ROUTES ---

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Using the default hashing method
        hashed_pw = generate_password_hash(request.form['password'])
        new_user = User(username=request.form['username'], password=hashed_pw)
        try:
            db.session.add(new_user)
            db.session.commit()
            flash('Account created! Please login.', 'success')
            return redirect(url_for('login'))
        except:
            flash('Username already exists.', 'danger')
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and check_password_hash(user.password, request.form['password']):
            login_user(user)
            return redirect(url_for('index'))
        flash('Invalid username or password', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# --- LIBRARY ROUTES ---

@app.route('/')
@login_required
def index(): # 1. View Books
    books = Book.query.all()
    return render_template('index.html', books=books)

@app.route('/add', methods=['GET', 'POST'])
@login_required
def add(): # 2. Add Books
    if request.method == 'POST':
        title = request.form['title']
        author = request.form['author']
        stock = int(request.form['stock'])
        new_book = Book(title=title, author=author, total_stock=stock, available_stock=stock)
        db.session.add(new_book)
        db.session.commit()
        flash('Book added successfully!', 'success')
        return redirect(url_for('index'))
    return render_template('add.html')

@app.route('/update_list')
@login_required
def update_list(): # 3. Update Stock List
    books = Book.query.all()
    return render_template('update.html', books=books)

@app.route('/borrow_list')
@login_required
def borrow_list(): # 4. Borrow List
    books = Book.query.all()
    return render_template('borrow.html', books=books)

@app.route('/action/<string:act>/<int:id>')
@login_required
def book_action(act, id):
    book = Book.query.get_or_404(id)
    
    # Logic for Borrowing/Returning
    if act == 'borrow' and book.available_stock > 0:
        book.available_stock -= 1
        
        # Log the transaction
        new_transaction = Transaction(book_id=book.id, user_id=current_user.id)
        db.session.add(new_transaction)
        
        flash(f'Borrowed {book.title}', 'info')
    elif act == 'return' and book.available_stock < book.total_stock:
        # Find active transaction for this user and book
        transaction = Transaction.query.filter_by(
            book_id=book.id, 
            user_id=current_user.id, 
            return_date=None
        ).first()
        
        if transaction:
            book.available_stock += 1
            transaction.return_date = datetime.now(timezone.utc)
            flash(f'Returned {book.title}', 'success')
        else:
            flash(f'You do not have an active session for resolving {book.title}.', 'danger')
        
    # Logic for Updating Total Inventory
    elif act == 'add_total':
        book.total_stock += 1
        book.available_stock += 1
    elif act == 'sub_total' and book.total_stock > 0:
        book.total_stock -= 1
        if book.available_stock > book.total_stock:
            book.available_stock = book.total_stock
            
    db.session.commit()
    return redirect(request.referrer)

@app.route('/dashboard_add_stock/<int:id>', methods=['POST'])
@login_required
def dashboard_add_stock(id):
    book = Book.query.get_or_404(id)
    quantity = request.form.get('quantity', type=int)
    
    if quantity and quantity > 0:
        book.total_stock += quantity
        book.available_stock += quantity
        db.session.commit()
        flash(f'Successfully added {quantity} copies of "{book.title}"', 'success')
    else:
        flash('Invalid quantity.', 'danger')
        
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard(): # 5. View Insights
    # 1. Total titles (count of Book records)
    total_titles = Book.query.count()
    
    # 2. Total Books Owned (sum of all total_stock)
    # Using python sum on query, for better scalability use db.func.sum
    all_books = Book.query.all()
    total_books_owned = sum(book.total_stock for book in all_books)
    
    # 3. Books currently borrowed
    books_borrowed = sum((book.total_stock - book.available_stock) for book in all_books)
    
    # 4. Low stock books (available stock <= 2)
    low_stock_books = Book.query.filter(Book.available_stock <= 2).all()
    
    # 5. Demand Prediction (Trending Books)
    # Find books with the most transactions in the last 30 days
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    
    # Query to count transactions per book
    trending_query = db.session.query(
        Book, 
        func.count(Transaction.id).label('borrow_count')
    ).join(Transaction, Book.id == Transaction.book_id)\
     .filter(Transaction.issue_date >= thirty_days_ago)\
     .group_by(Book.id)\
     .order_by(func.count(Transaction.id).desc())\
     .limit(5).all()

    return render_template('dashboard.html', 
                           total_titles=total_titles,
                           total_books_owned=total_books_owned,
                           books_borrowed=books_borrowed,
                           low_stock_books=low_stock_books,
                           trending_query=trending_query)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5001)