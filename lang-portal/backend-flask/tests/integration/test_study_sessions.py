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
        
        cursor.execute('''
            CREATE TABLE groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE study_activities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE study_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER NOT NULL,
                study_activity_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (group_id) REFERENCES groups (id),
                FOREIGN KEY (study_activity_id) REFERENCES study_activities (id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE words (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                spanish TEXT NOT NULL,
                english TEXT NOT NULL
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE word_review_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                study_session_id INTEGER NOT NULL,
                word_id INTEGER NOT NULL,
                correct BOOLEAN NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (study_session_id) REFERENCES study_sessions (id),
                FOREIGN KEY (word_id) REFERENCES words (id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE word_reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                word_id INTEGER NOT NULL UNIQUE,
                correct_count INTEGER DEFAULT 0,
                wrong_count INTEGER DEFAULT 0,
                FOREIGN KEY (word_id) REFERENCES words (id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS word_review_items_stats (
                word_id INTEGER PRIMARY KEY,
                correct_count INTEGER DEFAULT 0,
                wrong_count INTEGER DEFAULT 0,
                last_reviewed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (word_id) REFERENCES words (id)
            )
        ''')
        
        app.db.commit()
    
    # Import and register routes
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
    
    # Insert test word
    cursor.execute(
        'INSERT INTO words (spanish, english) VALUES (?, ?)',
        ('hola', 'hello')
    )
    test_word_id = cursor.lastrowid
    
    # Initialize word review counts
    cursor.execute('''
        INSERT INTO word_reviews (word_id, correct_count, wrong_count)
        VALUES (?, 0, 0)
    ''', (test_word_id,))
    
    app.db.commit()
    
    return {
        'group_id': test_group_id,
        'activity_id': test_activity_id,
        'word_id': test_word_id
    }

@pytest.fixture(autouse=True)
def setup_db(app):
    """Setup test database with required tables"""
    with app.app_context():
        cursor = app.db.cursor()
        # Create stats table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS word_review_items_stats (
                word_id INTEGER PRIMARY KEY,
                correct_count INTEGER DEFAULT 0,
                wrong_count INTEGER DEFAULT 0,
                last_reviewed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (word_id) REFERENCES words (id)
            )
        ''')
        app.db.commit()
        yield

def test_create_study_session_integration(client, app, test_data):
    """Test creating a study session through API"""
    response = client.post('/api/study_sessions', json={
        'group_id': test_data['group_id'],
        'study_activity_id': test_data['activity_id']
    })
    
    assert response.status_code == 201
    data = response.get_json()
    
    assert 'id' in data
    assert data['group_id'] == test_data['group_id']
    assert data['study_activity_id'] == test_data['activity_id']
    assert data['group_name'] == 'Test Group'
    assert data['activity_name'] == 'Test Activity'

def test_create_study_session_invalid_input(client, app):
    """Test creating session with invalid input"""
    # Missing required fields
    response = client.post('/api/study_sessions', json={})
    assert response.status_code == 400
    
    # Invalid types
    response = client.post('/api/study_sessions', json={
        'group_id': 'invalid',
        'study_activity_id': 1
    })
    assert response.status_code == 400

def test_create_study_session_nonexistent_group_integration(client, app, test_data):
    """Test creating a session with non-existent group"""
    response = client.post('/api/study_sessions', json={
        'group_id': 9999,  # Non-existent group
        'study_activity_id': test_data['activity_id']
    })
    
    assert response.status_code == 404
    assert response.get_json()['error'] == "Group or study activity not found"
    
    # Verify no session was created
    cursor = app.db.cursor()
    cursor.execute('SELECT COUNT(*) as count FROM study_sessions')
    count = cursor.fetchone()['count']
    assert count == 0

def test_create_study_session_nonexistent_activity_integration(client, app, test_data):
    """Test creating a session with non-existent activity"""
    response = client.post('/api/study_sessions', json={
        'group_id': test_data['group_id'],
        'study_activity_id': 9999  # Non-existent activity
    })
    
    assert response.status_code == 404
    assert response.get_json()['error'] == "Group or study activity not found"
    
    # Verify no session was created
    cursor = app.db.cursor()
    cursor.execute('SELECT COUNT(*) as count FROM study_sessions')
    count = cursor.fetchone()['count']
    assert count == 0

def test_create_multiple_sessions_integration(client, app, test_data):
    """Test creating multiple study sessions"""
    # Create first session
    response1 = client.post('/api/study_sessions', json={
        'group_id': test_data['group_id'],
        'study_activity_id': test_data['activity_id']
    })
    assert response1.status_code == 201
    
    # Create second session
    response2 = client.post('/api/study_sessions', json={
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

def test_review_word_integration(client, app, test_data):
    """Test reviewing a word through API"""
    # First create a session
    response = client.post('/api/study_sessions', json={
        'group_id': test_data['group_id'],
        'study_activity_id': test_data['activity_id']
    })
    session_id = response.get_json()['id']
    
    # Then review a word
    response = client.post(
        f'/api/study_sessions/{session_id}/words/{test_data["word_id"]}/review',
        json={'correct': True}
    )
    
    assert response.status_code == 200
    data = response.get_json()
    
    assert data['success'] is True
    assert data['word_id'] == test_data['word_id']
    assert data['study_session_id'] == session_id
    assert data['correct'] is True

def test_review_word_invalid_input(client, app, test_data):
    """Test reviewing word with invalid input"""
    # Missing correct field
    response = client.post(
        f'/api/study_sessions/1/words/1/review',
        json={}
    )
    assert response.status_code == 400
    
    # Invalid session ID
    response = client.post(
        f'/api/study_sessions/999/words/1/review',
        json={'correct': True}
    )
    assert response.status_code == 404
    
    # Invalid word ID
    response = client.post(
        f'/api/study_sessions/1/words/999/review',
        json={'correct': True}
    )
    assert response.status_code == 404

def test_review_word_integration_multiple_reviews(client, app, test_data):
    """Test submitting multiple reviews for the same word"""
    # Create session and word
    response = client.post('/api/study_sessions', json={
        'group_id': test_data['group_id'],
        'study_activity_id': test_data['activity_id']
    })
    session_data = response.get_json()
    
    cursor = app.db.cursor()
    cursor.execute(
        'INSERT INTO words (spanish, english) VALUES (?, ?)',
        ('hola', 'hello')
    )
    word_id = cursor.lastrowid
    
    # Initialize word review counts
    cursor.execute('''
        INSERT INTO word_reviews (word_id, correct_count, wrong_count)
        VALUES (?, 0, 0)
    ''', (word_id,))
    
    app.db.commit()
    
    # Submit first review (incorrect)
    response1 = client.post(
        f'/api/study_sessions/{session_data["id"]}/words/{word_id}/review',
        json={'correct': False}
    )
    assert response1.status_code == 200
    
    # Submit second review (correct)
    response2 = client.post(
        f'/api/study_sessions/{session_data["id"]}/words/{word_id}/review',
        json={'correct': True}
    )
    assert response2.status_code == 200
    
    # Verify both reviews exist in database
    cursor.execute('''
        SELECT correct
        FROM word_review_items
        WHERE study_session_id = ? AND word_id = ?
        ORDER BY created_at
    ''', (session_data['id'], word_id))
    
    reviews = cursor.fetchall()
    assert len(reviews) == 2
    assert reviews[0]['correct'] == 0  # First review (incorrect)
    assert reviews[1]['correct'] == 1  # Second review (correct)

def test_review_word_integration_nonexistent_session(client, app, test_data):
    """Test reviewing a word for a non-existent session"""
    response = client.post(
        f'/api/study_sessions/999/words/{test_data["word_id"]}/review',
        json={'correct': True}
    )
    
    assert response.status_code == 404
    data = response.get_json()
    assert data['error'] == "Study session or word not found"

def test_review_word_integration_nonexistent_word(client, app, test_data):
    """Test reviewing a non-existent word"""
    # Create study session
    response = client.post('/api/study_sessions', json={
        'group_id': test_data['group_id'],
        'study_activity_id': test_data['activity_id']
    })
    session_id = response.get_json()['id']
    
    # Try to review non-existent word
    response = client.post(
        f'/api/study_sessions/{session_id}/words/999/review',
        json={'correct': True}
    )
    
    assert response.status_code == 404
    data = response.get_json()
    assert data['error'] == "Study session or word not found" 