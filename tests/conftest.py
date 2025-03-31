import pytest
import sqlite3
import os
from app import create_app, init_db

@pytest.fixture
def app():
    """Create test app instance"""
    # Remove test database if it exists
    if os.path.exists('test.db'):
        os.remove('test.db')
        
    app = create_app()
    app.config['TESTING'] = True
    app.config['DATABASE'] = 'test.db'
    
    # Initialize database with schema
    with app.app_context():
        init_db()  # Use the app's own init_db function
        
    return app

@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()

@pytest.fixture
def init_test_data(app):
    """Initialize test data"""
    with app.app_context():
        cursor = app.db.cursor()
        cursor.executescript('''
            INSERT INTO groups (id, name) VALUES (1, 'Test Group');
            INSERT INTO study_activities (id, name, launch_url) 
            VALUES (1, 'Test Activity', 'http://test.com');
            INSERT INTO words (id, spanish, english, group_id)
            VALUES (1, 'gato', 'cat', 1);
        ''')
        app.db.commit() 