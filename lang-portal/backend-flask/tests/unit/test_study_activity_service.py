import pytest
import sqlite3
from services.study_activity_service import StudyActivityService

@pytest.fixture
def db():
    """Create test database"""
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE study_activities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            launch_url TEXT NOT NULL,
            preview_url TEXT NOT NULL
        )
    ''')
    return conn

@pytest.fixture
def service(db):
    return StudyActivityService(db)

@pytest.fixture
def test_data(db):
    """Insert test activity"""
    cursor = db.cursor()
    cursor.execute('''
        INSERT INTO study_activities (name, launch_url, preview_url)
        VALUES (?, ?, ?)
    ''', ('Flashcards', 'http://example.com/flashcards', 'http://example.com/preview.jpg'))
    activity_id = cursor.lastrowid
    db.commit()
    return {'activity_id': activity_id}

def test_get_all_activities(service, test_data):
    """Test getting all activities"""
    activities = service.get_all_activities()
    assert len(activities) == 1
    assert activities[0]['name'] == 'Flashcards'

def test_get_activity(service, test_data):
    """Test getting single activity"""
    activity = service.get_activity(test_data['activity_id'])
    assert activity is not None
    assert activity['name'] == 'Flashcards'

def test_get_nonexistent_activity(service):
    """Test getting non-existent activity"""
    activity = service.get_activity(999)
    assert activity is None

def test_create_activity(service):
    """Test creating new activity"""
    activity = service.create_activity(
        name='Quiz',
        launch_url='http://example.com/quiz',
        preview_url='http://example.com/preview.jpg'
    )
    assert activity['name'] == 'Quiz'
    assert activity['launch_url'] == 'http://example.com/quiz' 