import pytest
from flask import Flask
import sqlite3

@pytest.fixture
def app():
    """Create test app with database"""
    app = Flask(__name__)
    app.db = sqlite3.connect(':memory:', check_same_thread=False)
    app.db.row_factory = sqlite3.Row
    
    with app.app_context():
        cursor = app.db.cursor()
        cursor.execute('''
            CREATE TABLE study_activities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT
            )
        ''')
        app.db.commit()
    
    from routes.study_activities import load
    load(app)
    
    return app

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def test_data(app):
    """Insert test activities"""
    cursor = app.db.cursor()
    cursor.execute('''
        INSERT INTO study_activities (name, description)
        VALUES (?, ?)
    ''', ('Flashcards', 'Practice with flashcards'))
    activity_id = cursor.lastrowid
    app.db.commit()
    return {'activity_id': activity_id}

def test_get_activities_integration(client):
    """Test getting all activities"""
    response = client.get('/api/study_activities')
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)

def test_get_activity_integration(client, test_data):
    """Test getting single activity"""
    response = client.get(f'/api/study_activities/{test_data["activity_id"]}')
    assert response.status_code == 200
    data = response.get_json()
    assert data['name'] == 'Flashcards'
    assert data['description'] == 'Practice with flashcards'

def test_get_nonexistent_activity_integration(client):
    """Test getting non-existent activity"""
    response = client.get('/api/study_activities/999')
    assert response.status_code == 404

def test_create_activity_integration(client):
    """Test creating new activity"""
    response = client.post('/api/study_activities', json={
        'name': 'Quiz',
        'description': 'Test your knowledge'
    })
    assert response.status_code == 201
    data = response.get_json()
    assert data['name'] == 'Quiz'
    assert data['description'] == 'Test your knowledge'

def test_create_activity_missing_name_integration(client):
    """Test creating activity without name"""
    response = client.post('/api/study_activities', json={
        'description': 'Test your knowledge'
    })
    assert response.status_code == 400 