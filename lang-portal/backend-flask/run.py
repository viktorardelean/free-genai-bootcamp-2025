import os
from pathlib import Path
from db.init_db import main as init_db
from app import app

if __name__ == '__main__':
    # Remove old database if it exists
    db_path = Path('words.db')
    if db_path.exists():
        os.remove(db_path)
    
    # Initialize database
    init_db()
    
    # Run Flask app
    app.run(debug=True, port=5001) 