import pytest

@pytest.fixture
def test_client(app):
    """Create a test client"""
    return app.test_client()

@pytest.fixture(autouse=True)
def setup_database(app, init_db):
    """Set up test database"""
    with app.app_context():
        cursor = app.db.cursor()
        
        # Debug: Check if we can query SQLite master table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print("Existing tables:", tables)  # See what tables exist
        
        # Create required tables
        cursor.executescript('''
            CREATE TABLE IF NOT EXISTS groups (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL
            );
            
            CREATE TABLE IF NOT EXISTS study_activities (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                launch_url TEXT,
                preview_url TEXT
            );
            
            CREATE TABLE IF NOT EXISTS words (
                id INTEGER PRIMARY KEY,
                spanish TEXT NOT NULL,
                english TEXT NOT NULL,
                group_id INTEGER NOT NULL,
                FOREIGN KEY (group_id) REFERENCES groups (id)
            );
        ''')
        
        # Debug: Verify tables were created
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print("Tables after creation:", tables)
        
        # Clean existing data
        cursor.executescript('''
            DELETE FROM words;
            DELETE FROM study_activities;
            DELETE FROM groups;
        ''')
        
        # Add test data
        cursor.executescript('''
            INSERT INTO groups (id, name) VALUES (1, 'Test Group');
            INSERT INTO study_activities (id, name, launch_url) 
            VALUES (1, 'Test Activity', 'http://test.com');
            INSERT INTO words (id, spanish, english, group_id)
            VALUES (1, 'gato', 'cat', 1);
        ''')
        
        app.db.commit()
        
    yield

