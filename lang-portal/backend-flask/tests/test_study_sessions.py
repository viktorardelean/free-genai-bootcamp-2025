import pytest
from datetime import datetime
from unittest.mock import Mock
from flask import Flask
from routes.study_sessions import ERROR_MESSAGES  # Import ERROR_MESSAGES constant

def test_create_study_session_success(client, app):
    """Test successful creation of a study session"""
    # Mock data
    test_group = {'id': 1, 'name': 'Test Group'}
    test_activity = {'id': 1, 'name': 'Test Activity'}
    
    # Mock database cursor
    cursor = Mock()
    app.db.cursor = Mock(return_value=cursor)
    
    # Mock foreign key checks
    cursor.fetchone.side_effect = [
        test_group,  # For group check
        test_activity,  # For activity check
        {  # For final session fetch
            'id': 1,
            'group_id': test_group['id'],
            'group_name': test_group['name'],
            'activity_id': test_activity['id'],
            'activity_name': test_activity['name'],
            'created_at': datetime.now(),
            'review_items_count': 0
        }
    ]
    
    # Test request
    response = client.post('/api/study-sessions', json={
        'group_id': test_group['id'],
        'study_activity_id': test_activity['id']
    })
    
    # Assertions
    assert response.status_code == 201
    data = response.get_json()
    assert data['id'] == 1
    assert data['group_id'] == test_group['id']
    assert data['group_name'] == test_group['name']
    assert data['activity_id'] == test_activity['id']
    assert data['activity_name'] == test_activity['name']
    assert 'start_time' in data
    assert 'end_time' in data
    assert data['review_items_count'] == 0

def test_create_study_session_missing_fields(client):
    """Test error handling when required fields are missing"""
    # Test with missing group_id
    response = client.post('/api/study-sessions', json={
        'study_activity_id': 1
    })
    assert response.status_code == 400
    assert response.get_json()['error'] == "Missing required fields: group_id or study_activity_id"
    
    # Test with missing study_activity_id
    response = client.post('/api/study-sessions', json={
        'group_id': 1
    })
    assert response.status_code == 400
    assert response.get_json()['error'] == "Missing required fields: group_id or study_activity_id"

def test_create_study_session_invalid_types(client):
    """Test error handling when field types are invalid"""
    response = client.post('/api/study-sessions', json={
        'group_id': "1",  # String instead of int
        'study_activity_id': 1
    })
    assert response.status_code == 400
    assert response.get_json()['error'] == "group_id and study_activity_id must be integers"

def test_create_study_session_group_not_found(client, app):
    """Test error handling when group doesn't exist"""
    # Mock cursor
    cursor = Mock()
    app.db.cursor = Mock(return_value=cursor)
    cursor.fetchone.return_value = None  # Group not found
    
    response = client.post('/api/study-sessions', json={
        'group_id': 999,
        'study_activity_id': 1
    })
    assert response.status_code == 404
    assert response.get_json()['error'] == "Group not found"

def test_create_study_session_activity_not_found(client, app):
    """Test error handling when activity doesn't exist"""
    # Mock cursor
    cursor = Mock()
    app.db.cursor = Mock(return_value=cursor)
    cursor.fetchone.side_effect = [
        {'id': 1},  # Group exists
        None  # Activity not found
    ]
    
    response = client.post('/api/study-sessions', json={
        'group_id': 1,
        'study_activity_id': 999
    })
    assert response.status_code == 404
    assert response.get_json()['error'] == "Study activity not found"

def test_create_study_session_db_error(client, app):
    """Test error handling when database operation fails"""
    # Mock cursor to raise an exception
    cursor = Mock()
    app.db.cursor = Mock(return_value=cursor)
    cursor.fetchone.side_effect = Exception("Database error")
    
    response = client.post('/api/study-sessions', json={
        'group_id': 1,
        'study_activity_id': 1
    })
    assert response.status_code == 500
    assert 'error' in response.get_json()

def test_review_word_in_session_success(client, app):
    """Test successful word review creation"""
    # Mock data
    test_session = {'id': 1}
    test_word = {'id': 1, 'spanish': 'hola', 'english': 'hello'}
    test_review = {
        'id': 1,
        'study_session_id': test_session['id'],
        'word_id': test_word['id'],
        'spanish': test_word['spanish'],
        'english': test_word['english'],
        'correct': True,
        'created_at': datetime.now()
    }
    
    # Mock database cursor
    cursor = Mock()
    app.db.cursor = Mock(return_value=cursor)
    
    # Mock database checks and insert
    cursor.fetchone.side_effect = [
        test_session,  # Session exists check
        test_word,     # Word exists check
        test_review    # Final review fetch
    ]
    cursor.lastrowid = test_review['id']
    
    # Test request - Note the URL format matches the route exactly
    response = client.post(f'/api/study-sessions/{test_session["id"]}/words/{test_word["id"]}/review', 
                          json={'correct': True})
    
    # Add debug output
    print(f"Response: {response.status_code} - {response.get_json()}")
    
    # Assertions
    assert response.status_code == 201
    data = response.get_json()
    assert data['id'] == test_review['id']
    assert data['study_session_id'] == test_session['id']
    assert data['word_id'] == test_word['id']
    assert data['word_spanish'] == test_word['spanish']
    assert data['word_english'] == test_word['english']
    assert data['correct'] is True
    assert 'created_at' in data

def test_review_word_missing_correct_field(client):
    """Test error handling when correct field is missing"""
    response = client.post('/api/study-sessions/1/words/1/review', 
                          json={})
    assert response.status_code == 400
    assert response.get_json()['error'] == "Missing required field: correct"

def test_review_word_invalid_correct_type(client):
    """Test error handling when correct field is not boolean"""
    response = client.post('/api/study-sessions/1/words/1/review', 
                          json={'correct': "true"})
    assert response.status_code == 400
    assert response.get_json()['error'] == "Field 'correct' must be a boolean"

def test_review_word_session_not_found(client, app):
    """Test error handling when session doesn't exist"""
    cursor = Mock()
    app.db.cursor = Mock(return_value=cursor)
    cursor.fetchone.return_value = None  # Session not found
    
    response = client.post('/api/study-sessions/999/words/1/review', 
                          json={'correct': True})
    
    # Add debug output
    print(f"Response: {response.status_code} - {response.get_json()}")
    
    assert response.status_code == 404
    assert response.get_json() is not None  # Ensure we get a JSON response
    assert response.get_json()['error'] == ERROR_MESSAGES['SESSION_NOT_FOUND']

def test_review_word_not_found(client, app):
    """Test error handling when word doesn't exist"""
    # Mock cursor
    cursor = Mock()
    app.db.cursor = Mock(return_value=cursor)
    cursor.fetchone.side_effect = [
        {'id': 1},  # Session exists
        None        # Word not found
    ]
    
    response = client.post('/api/study-sessions/1/words/999/review', 
                          json={'correct': True})
    assert response.status_code == 404
    assert response.get_json()['error'] == "Word not found"

def test_review_word_db_error(client, app):
    """Test error handling when database operation fails"""
    # Mock cursor to raise an exception
    cursor = Mock()
    app.db.cursor = Mock(return_value=cursor)
    cursor.fetchone.side_effect = Exception("Database error")
    
    response = client.post('/api/study-sessions/1/words/1/review', 
                          json={'correct': True})
    assert response.status_code == 500
    assert 'error' in response.get_json()

def test_review_word_incorrect_answer(client, app):
    """Test review creation with incorrect answer"""
    # Mock data
    test_session = {'id': 1}
    test_word = {'id': 1, 'spanish': 'hola', 'english': 'hello'}
    test_review = {
        'id': 1,
        'study_session_id': test_session['id'],
        'word_id': test_word['id'],
        'spanish': test_word['spanish'],
        'english': test_word['english'],
        'correct': False,
        'created_at': datetime.now()
    }
    
    cursor = Mock()
    app.db.cursor = Mock(return_value=cursor)
    cursor.fetchone.side_effect = [test_session, test_word, test_review]
    cursor.lastrowid = test_review['id']
    
    response = client.post(f'/api/study-sessions/{test_session["id"]}/words/{test_word["id"]}/review', 
                          json={'correct': False})
    
    assert response.status_code == 201
    data = response.get_json()
    assert data['correct'] is False

def test_review_word_invalid_json(client, app):
    """Test error handling with invalid JSON payload"""
    # Mock cursor to prevent DB access
    cursor = Mock()
    app.db.cursor = Mock(return_value=cursor)
    
    response = client.post('/api/study-sessions/1/words/1/review', 
                          data="invalid json",
                          content_type='application/json')
    
    # Add debug output
    print(f"Response: {response.status_code} - {response.get_json()}")
    
    assert response.status_code == 400
    data = response.get_json()
    assert 'error' in data
    assert 'Invalid JSON' in data['error']

def test_review_word_multiple_reviews(client, app):
    """Test multiple reviews for same word in session"""
    # Mock data for first review
    test_session = {'id': 1}
    test_word = {'id': 1, 'spanish': 'hola', 'english': 'hello'}
    
    cursor = Mock()
    app.db.cursor = Mock(return_value=cursor)
    
    # First review (incorrect)
    first_review = {
        'id': 1,
        'study_session_id': test_session['id'],
        'word_id': test_word['id'],
        'spanish': test_word['spanish'],
        'english': test_word['english'],
        'correct': False,
        'created_at': datetime.now()
    }
    cursor.fetchone.side_effect = [test_session, test_word, first_review]
    cursor.lastrowid = first_review['id']
    
    response1 = client.post(f'/api/study-sessions/{test_session["id"]}/words/{test_word["id"]}/review', 
                           json={'correct': False})
    assert response1.status_code == 201
    
    # Second review (correct)
    second_review = {**first_review, 'id': 2, 'correct': True}
    cursor.fetchone.side_effect = [test_session, test_word, second_review]
    cursor.lastrowid = second_review['id']
    
    response2 = client.post(f'/api/study-sessions/{test_session["id"]}/words/{test_word["id"]}/review', 
                           json={'correct': True})
    assert response2.status_code == 201
    
    # Verify different review IDs
    assert response1.get_json()['id'] != response2.get_json()['id']

def test_review_word_missing_content_type(client, app):
    """Test error handling when content-type header is missing"""
    # Mock cursor to prevent DB access
    cursor = Mock()
    app.db.cursor = Mock(return_value=cursor)
    
    response = client.post('/api/study-sessions/1/words/1/review', 
                          data='{"correct": true}')
    
    # Add debug output
    print(f"Response: {response.status_code} - {response.get_json()}")
    
    assert response.status_code == 400
    data = response.get_json()
    assert 'error' in data
    assert 'Content-Type must be application/json' in data['error']

def test_review_word_null_correct_value(client):
    """Test error handling when correct is null"""
    response = client.post('/api/study-sessions/1/words/1/review', 
                          json={'correct': None})
    assert response.status_code == 400
    assert response.get_json()['error'] == "Missing required field: correct"

@pytest.fixture
def app():
    """Test app fixture with mocked db"""
    app = Flask(__name__)
    app.db = Mock()  # Mock the database
    
    # Import and register routes
    from routes.study_sessions import load
    load(app)
    
    # Important: Configure testing mode
    app.config['TESTING'] = True
    return app

@pytest.fixture
def client(app):
    """Test client fixture"""
    return app.test_client() 