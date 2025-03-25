import sqlite3
import os
import json
from pathlib import Path

def init_db():
    """Initialize the database and run migrations"""
    db_path = Path(__file__).parent.parent / 'words.db'
    migrations_path = Path(__file__).parent / 'migrations'
    
    # Connect to database (creates it if it doesn't exist)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    try:
        # Create migrations table if it doesn't exist
        conn.execute('''
            CREATE TABLE IF NOT EXISTS migrations (
                filename TEXT PRIMARY KEY,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Run migrations in order
        for migration_file in sorted(migrations_path.glob('*.sql')):
            # Check if migration was already applied
            cursor = conn.cursor()
            cursor.execute('SELECT filename FROM migrations WHERE filename = ?', 
                         (migration_file.name,))
            if cursor.fetchone() is None:
                print(f"Running migration: {migration_file.name}")
                with open(migration_file) as f:
                    conn.executescript(f.read())
                # Record that this migration was applied
                conn.execute('INSERT INTO migrations (filename) VALUES (?)', 
                           (migration_file.name,))
                conn.commit()
            else:
                print(f"Skipping migration {migration_file.name} - already applied")
        
        print("Database initialized successfully")
        
    except Exception as e:
        print(f"Error initializing database: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

def seed_db(conn, seed_file, group_name):
    """Seed database with words from a JSON file"""
    cursor = conn.cursor()
    
    try:
        # Create group if it doesn't exist
        cursor.execute('INSERT OR IGNORE INTO groups (name) VALUES (?)', (group_name,))
        cursor.execute('SELECT id FROM groups WHERE name = ?', (group_name,))
        group_id = cursor.fetchone()['id']
        
        # Read and insert words
        with open(seed_file) as f:
            words = json.load(f)
            
        for word in words:
            # Insert word
            cursor.execute(
                'INSERT OR IGNORE INTO words (spanish, english) VALUES (?, ?)',
                (word['spanish'], word['english'])
            )
            cursor.execute('SELECT id FROM words WHERE spanish = ? AND english = ?',
                         (word['spanish'], word['english']))
            word_id = cursor.fetchone()['id']
            
            # Create word-group association (if doesn't exist)
            cursor.execute('''
                INSERT OR IGNORE INTO word_groups (word_id, group_id) 
                VALUES (?, ?)
            ''', (word_id, group_id))
        
        conn.commit()
        print(f"Seeded {len(words)} words into group '{group_name}'")
        
    except Exception as e:
        print(f"Error seeding data: {e}")
        conn.rollback()
        raise

def main():
    """Main entry point for database initialization"""
    # Initialize database
    init_db()
    
    # Connect for seeding
    db_path = Path(__file__).parent.parent / 'words.db'
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    try:
        # Define seed files and their groups
        seeds = [
            ('db/seeds/animals.json', 'Animals'),
            ('db/seeds/colors.json', 'Colors'),
            ('db/seeds/numbers.json', 'Numbers'),
            ('db/seeds/food.json', 'Food'),
            ('db/seeds/family.json', 'Family')
        ]
        
        # Run all seeds
        for seed_file, group_name in seeds:
            seed_db(conn, seed_file, group_name)
            
    finally:
        conn.close()

if __name__ == '__main__':
    main() 