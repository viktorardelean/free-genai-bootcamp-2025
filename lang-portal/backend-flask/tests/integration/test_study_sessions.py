import pytest
from datetime import datetime
from flask import Flask
import sqlite3

@pytest.fixture
def app():
    """Create test app with real database connection"""
    app = Flask(__name__)
    
    # Use an in-memory SQLite database for testing
    app.db = sqlite3.connect(':memory:', check_same_thread=False)
    app.db.row_factory = sqlite3.Row
    
    # Create test tables
    with app.app_context():
        cursor = app.db.cursor()
        
        # Create groups table
        cursor.execute('''
            CREATE TABLE groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL
            )
        ''')
        
        # Create study_activities table
        cursor.execute('''
            CREATE TABLE study_activities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL
            )
        ''')
        
        # Create study_sessions table
        cursor.execute('''
            CREATE TABLE study_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER NOT NULL,
                study_activity_id INTEGER NOT NULL,
                created_at TIMESTAMP NOT NULL,
                FOREIGN KEY (group_id) REFERENCES groups (id),
                FOREIGN KEY (study_activity_id) REFERENCES study_activities (id)
            )
        ''')
        
        # Create word_review_items table
        cursor.execute('''
            CREATE TABLE word_review_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                study_session_id INTEGER NOT NULL,
                FOREIGN KEY (study_session_id) REFERENCES study_sessions (id)
            )
        ''')
        
        app.db.commit()
    
    # Import and load routes
    from routes.study_sessions import load
    load(app)
    
    return app

@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()

@pytest.fixture
def test_data(app):
    """Insert test data into database"""
    cursor = app.db.cursor()
    
    # Insert test group
    cursor.execute(
        'INSERT INTO groups (name) VALUES (?)',
        ('Test Group',)
    )
    test_group_id = cursor.lastrowid
    
    # Insert test activity
    cursor.execute(
        'INSERT INTO study_activities (name) VALUES (?)',
        ('Test Activity',)
    )
    test_activity_id = cursor.lastrowid
    
    app.db.commit()
    
    return {
        'group_id': test_group_id,
        'activity_id': test_activity_id
    }

def test_create_study_session_integration(client, app, test_data):
    """Test creating a study session with actual database interaction"""
    # Make request to create session
    response = client.post('/api/study-sessions', json={
        'group_id': test_data['group_id'],
        'study_activity_id': test_data['activity_id']
    })
    
    # Check response
    assert response.status_code == 201
    data = response.get_json()
    assert data['group_id'] == test_data['group_id']
    assert data['group_name'] == 'Test Group'
    assert data['activity_id'] == test_data['activity_id']
    assert data['activity_name'] == 'Test Activity'
    assert data['review_items_count'] == 0
    
    # Verify database state
    cursor = app.db.cursor()
    cursor.execute('''
        SELECT 
            ss.id,
            ss.group_id,
            g.name as group_name,
            sa.id as activity_id,
            sa.name as activity_name,
            ss.created_at
        FROM study_sessions ss
        JOIN groups g ON g.id = ss.group_id
        JOIN study_activities sa ON sa.id = ss.study_activity_id
        WHERE ss.id = ?
    ''', (data['id'],))
    
    session = cursor.fetchone()
    assert session is not None
    assert session['group_id'] == test_data['group_id']
    assert session['group_name'] == 'Test Group'
    assert session['activity_id'] == test_data['activity_id']
    assert session['activity_name'] == 'Test Activity'

def test_create_study_session_nonexistent_group_integration(client, app, test_data):
    """Test creating a session with non-existent group"""
    response = client.post('/api/study-sessions', json={
        'group_id': 9999,  # Non-existent group
        'study_activity_id': test_data['activity_id']
    })
    
    assert response.status_code == 404
    assert response.get_json()['error'] == "Group not found"
    
    # Verify no session was created
    cursor = app.db.cursor()
    cursor.execute('SELECT COUNT(*) as count FROM study_sessions')
    count = cursor.fetchone()['count']
    assert count == 0

def test_create_study_session_nonexistent_activity_integration(client, app, test_data):
    """Test creating a session with non-existent activity"""
    response = client.post('/api/study-sessions', json={
        'group_id': test_data['group_id'],
        'study_activity_id': 9999  # Non-existent activity
    })
    
    assert response.status_code == 404
    assert response.get_json()['error'] == "Study activity not found"
    
    # Verify no session was created
    cursor = app.db.cursor()
    cursor.execute('SELECT COUNT(*) as count FROM study_sessions')
    count = cursor.fetchone()['count']
    assert count == 0

def test_create_multiple_sessions_integration(client, app, test_data):
    """Test creating multiple study sessions"""
    # Create first session
    response1 = client.post('/api/study-sessions', json={
        'group_id': test_data['group_id'],
        'study_activity_id': test_data['activity_id']
    })
    assert response1.status_code == 201
    
    # Create second session
    response2 = client.post('/api/study-sessions', json={
        'group_id': test_data['group_id'],
        'study_activity_id': test_data['activity_id']
    })
    assert response2.status_code == 201
    
    # Verify both sessions exist and are different
    data1 = response1.get_json()
    data2 = response2.get_json()
    assert data1['id'] != data2['id']
    
    # Verify database state
    cursor = app.db.cursor()
    cursor.execute('SELECT COUNT(*) as count FROM study_sessions')
    count = cursor.fetchone()['count']
    assert count == 2 