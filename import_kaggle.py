import kagglehub
import pandas as pd
import os
import random
from app import app, db, Book  # Imports your app's context and models

def populate_database():
    """
    Downloads the Kaggle dataset, reads the CSV, and populates the Book table.
    """
    print("-> Starting Kaggle data import...")

    # 1. Download the dataset from Kaggle
    print("-> Downloading dataset from kagglehub...")
    try:
        path = kagglehub.dataset_download("ziya07/library-management")
    except Exception as e:
        print(f"Error downloading from Kaggle: {e}")
        print("Please ensure you are logged into Kaggle in your terminal.")
        return

    # 2. Find and read the CSV file using Pandas
    csv_file_path = os.path.join(path, 'library_dataset_random.csv') # This dataset's file is named library_dataset_random.csv
    if not os.path.exists(csv_file_path):
        print(f"Error: Could not find library_dataset_random.csv in the downloaded path: {path}")
        return
        
    print(f"-> Reading data from {csv_file_path}")
    # We will import the first 200 books for this example
    df = pd.read_csv(csv_file_path, on_bad_lines='skip').head(200)

    # 3. Push data into the Flask database
    with app.app_context():
        # Delete all old books before importing
        print("-> Deleting old books from the database...")
        db.session.query(Book).delete()

        print("-> Inserting books into the database...")
        for index, row in df.iterrows():
            # Match the column names from the Kaggle CSV ('Title', 'Author')
            title = row.get('Title')
            author = row.get('Author')
            
            if title and author and isinstance(title, str) and isinstance(author, str):
                stock = random.randint(1, 50)
                new_book = Book(
                    title=title,
                    author=author,
                    total_stock=stock,
                    available_stock=stock
                )
                db.session.add(new_book)
        
        db.session.commit()
        print(f"\n✅ Success! Imported {len(df)} books into your library.")

# This makes the script runnable from the command line
if __name__ == "__main__":
    populate_database()