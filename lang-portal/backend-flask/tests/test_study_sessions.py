import pytest
from datetime import datetime
from unittest.mock import Mock

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

@pytest.fixture
def client(app):
    """Test client fixture"""
    return app.test_client()

@pytest.fixture
def app():
    """Test app fixture with mocked db"""
    from flask import Flask
    app = Flask(__name__)
    app.db = Mock()  # Mock the database
    
    # Import and load routes
    from routes.study_sessions import load
    load(app)
    
    return app 