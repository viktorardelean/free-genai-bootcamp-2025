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
        
        # Create words table
        cursor.execute('''
            CREATE TABLE words (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                spanish TEXT NOT NULL,
                english TEXT NOT NULL
            )
        ''')

        # Create word_groups join table
        cursor.execute('''
            CREATE TABLE word_groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                word_id INTEGER NOT NULL,
                group_id INTEGER NOT NULL,
                FOREIGN KEY (word_id) REFERENCES words (id),
                FOREIGN KEY (group_id) REFERENCES groups (id)
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
                word_id INTEGER NOT NULL,
                correct BOOLEAN NOT NULL,
                created_at TIMESTAMP NOT NULL,
                FOREIGN KEY (study_session_id) REFERENCES study_sessions (id),
                FOREIGN KEY (word_id) REFERENCES words (id)
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

def test_review_word_integration_success(client, app, test_data):
    """Test creating a word review with actual database interaction"""
    # First create a study session
    response = client.post('/api/study-sessions', json={
        'group_id': test_data['group_id'],
        'study_activity_id': test_data['activity_id']
    })
    assert response.status_code == 201
    session_data = response.get_json()
    
    # Create a test word and associate it with the group
    cursor = app.db.cursor()
    cursor.execute(
        'INSERT INTO words (spanish, english) VALUES (?, ?)',
        ('hola', 'hello')
    )
    word_id = cursor.lastrowid
    
    # Add word to the group
    cursor.execute(
        'INSERT INTO word_groups (word_id, group_id) VALUES (?, ?)',
        (word_id, test_data['group_id'])
    )
    app.db.commit()
    
    # Submit a review
    response = client.post(
        f'/api/study-sessions/{session_data["id"]}/words/{word_id}/review',
        json={'correct': True}
    )
    
    # Add debug output
    print(f"Response: {response.status_code} - {response.get_json()}")
    
    # Check response
    assert response.status_code == 201
    data = response.get_json()
    assert data['study_session_id'] == session_data['id']
    assert data['word_id'] == word_id
    assert data['word_spanish'] == 'hola'
    assert data['word_english'] == 'hello'
    assert data['correct'] in (True, 1)
    
    # Verify database state
    cursor.execute('''
        SELECT 
            wri.correct,
            w.spanish,
            w.english,
            wg.group_id
        FROM word_review_items wri
        JOIN words w ON w.id = wri.word_id
        JOIN word_groups wg ON w.id = wg.word_id
        WHERE wri.study_session_id = ? AND wri.word_id = ?
    ''', (session_data['id'], word_id))
    
    review = cursor.fetchone()
    assert review is not None
    assert review['correct'] == 1
    assert review['spanish'] == 'hola'
    assert review['english'] == 'hello'
    assert review['group_id'] == test_data['group_id']

def test_review_word_integration_multiple_reviews(client, app, test_data):
    """Test submitting multiple reviews for the same word"""
    # Create session and word
    response = client.post('/api/study-sessions', json={
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
    app.db.commit()
    
    # Submit first review (incorrect)
    response1 = client.post(
        f'/api/study-sessions/{session_data["id"]}/words/{word_id}/review',
        json={'correct': False}
    )
    assert response1.status_code == 201
    
    # Submit second review (correct)
    response2 = client.post(
        f'/api/study-sessions/{session_data["id"]}/words/{word_id}/review',
        json={'correct': True}
    )
    assert response2.status_code == 201
    
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
    # Create test word
    cursor = app.db.cursor()
    cursor.execute(
        'INSERT INTO words (spanish, english) VALUES (?, ?)',
        ('hola', 'hello')
    )
    word_id = cursor.lastrowid
    app.db.commit()
    
    # Try to review with non-existent session
    response = client.post(
        f'/api/study-sessions/999/words/{word_id}/review',
        json={'correct': True}
    )
    
    assert response.status_code == 404
    assert response.get_json()['error'] == "Study session not found"
    
    # Verify no review was created
    cursor.execute('SELECT COUNT(*) as count FROM word_review_items')
    count = cursor.fetchone()['count']
    assert count == 0

def test_review_word_integration_nonexistent_word(client, app, test_data):
    """Test reviewing a non-existent word"""
    # Create study session
    response = client.post('/api/study-sessions', json={
        'group_id': test_data['group_id'],
        'study_activity_id': test_data['activity_id']
    })
    session_data = response.get_json()
    
    # Try to review non-existent word
    response = client.post(
        f'/api/study-sessions/{session_data["id"]}/words/999/review',
        json={'correct': True}
    )
    
    # Add debug output
    print(f"Response: {response.status_code} - {response.get_json()}")
    
    # Check response
    data = response.get_json()
    assert response.status_code == 404
    assert data['error'] == "Word not found"
    
    # Verify no review was created
    cursor = app.db.cursor()
    cursor.execute('SELECT COUNT(*) as count FROM word_review_items')
    count = cursor.fetchone()['count']
    assert count == 0

def test_review_word_integration_invalid_input(client, app, test_data):
    """Test reviewing with invalid input"""
    # Create session and word
    response = client.post('/api/study-sessions', json={
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
    app.db.commit()
    
    # Test with missing correct field
    response = client.post(
        f'/api/study-sessions/{session_data["id"]}/words/{word_id}/review',
        json={}
    )
    assert response.status_code == 400
    assert response.get_json()['error'] == "Missing required field: correct"
    
    # Test with invalid correct type
    response = client.post(
        f'/api/study-sessions/{session_data["id"]}/words/{word_id}/review',
        json={'correct': 'true'}
    )
    assert response.status_code == 400
    assert response.get_json()['error'] == "Field 'correct' must be a boolean"
    
    # Verify no reviews were created
    cursor.execute('SELECT COUNT(*) as count FROM word_review_items')
    count = cursor.fetchone()['count']
    assert count == 0 