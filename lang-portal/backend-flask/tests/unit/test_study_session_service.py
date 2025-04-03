import pytest
import sqlite3
from datetime import datetime
from services.study_session_service import StudySessionService, StudySession

@pytest.fixture
def db():
    """Create in-memory test database"""
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Create test tables
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
    
    return conn

@pytest.fixture
def service(db):
    """Create StudySessionService instance"""
    return StudySessionService(db)

@pytest.fixture
def test_data(db):
    """Create test data"""
    cursor = db.cursor()
    
    # Create test group
    cursor.execute('INSERT INTO groups (name) VALUES (?)', ('Test Group',))
    group_id = cursor.lastrowid
    
    # Create test activity
    cursor.execute('INSERT INTO study_activities (name) VALUES (?)', ('Test Activity',))
    activity_id = cursor.lastrowid
    
    # Create test word
    cursor.execute('INSERT INTO words (spanish, english) VALUES (?, ?)', ('hola', 'hello'))
    word_id = cursor.lastrowid
    
    db.commit()
    return {
        'group_id': group_id,
        'activity_id': activity_id,
        'word_id': word_id
    }

@pytest.fixture(autouse=True)
def setup_test_db(db):
    """Setup test database with required tables"""
    cursor = db.cursor()
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
    db.commit()
    yield

def test_create_session_success(service, test_data):
    """Test creating a study session successfully"""
    session = service.create_session(test_data['group_id'], test_data['activity_id'])
    
    assert isinstance(session, StudySession)
    assert session.group_id == test_data['group_id']
    assert session.study_activity_id == test_data['activity_id']
    assert session.group_name == 'Test Group'
    assert session.activity_name == 'Test Activity'

def test_create_session_nonexistent_group(service, test_data):
    """Test creating session with non-existent group"""
    session = service.create_session(999, test_data['activity_id'])
    assert session is None

def test_create_session_nonexistent_activity(service, test_data):
    """Test creating session with non-existent activity"""
    session = service.create_session(test_data['group_id'], 999)
    assert session is None

def test_review_word_success(service, test_data):
    """Test reviewing a word successfully"""
    # First create a session
    session = service.create_session(test_data['group_id'], test_data['activity_id'])
    
    # Then review a word
    result = service.review_word(session.id, test_data['word_id'], True)
    
    assert result is not None
    assert result['success'] is True
    assert result['word_id'] == test_data['word_id']
    assert result['study_session_id'] == session.id
    assert result['correct'] is True
    assert 'created_at' in result

def test_review_word_nonexistent_session(service, test_data):
    """Test reviewing word in non-existent session"""
    result = service.review_word(999, test_data['word_id'], True)
    assert result is None

def test_review_word_nonexistent_word(service, test_data):
    """Test reviewing non-existent word"""
    session = service.create_session(test_data['group_id'], test_data['activity_id'])
    result = service.review_word(session.id, 999, True)
    assert result is None

def test_review_word_updates_counts(service, test_data):
    """Test that reviewing updates word review counts"""
    session = service.create_session(test_data['group_id'], test_data['activity_id'])

    # Review word twice - once correct, once incorrect
    service.review_word(session.id, test_data['word_id'], True)
    service.review_word(session.id, test_data['word_id'], False)

    # Check counts in stats table
    cursor = service.db.cursor()
    cursor.execute('''
        SELECT correct_count, wrong_count 
        FROM word_review_items_stats 
        WHERE word_id = ?
    ''', (test_data['word_id'],))
    stats = cursor.fetchone()

    assert stats['correct_count'] == 1
    assert stats['wrong_count'] == 1 