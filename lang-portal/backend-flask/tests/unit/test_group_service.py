import pytest
import sqlite3
from services.group_service import GroupService
from models.word import Word

@pytest.fixture
def db():
    """Create in-memory test database"""
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Create test tables with updated schema
    cursor.execute('''
        CREATE TABLE groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            words_count INTEGER DEFAULT 0
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE words (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            spanish TEXT NOT NULL COLLATE NOCASE,
            english TEXT NOT NULL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE word_groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            word_id INTEGER NOT NULL,
            group_id INTEGER NOT NULL,
            UNIQUE(word_id, group_id),
            FOREIGN KEY (word_id) REFERENCES words (id),
            FOREIGN KEY (group_id) REFERENCES groups (id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE word_reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            word_id INTEGER NOT NULL,
            correct_count INTEGER DEFAULT 0,
            wrong_count INTEGER DEFAULT 0,
            FOREIGN KEY (word_id) REFERENCES words (id)
        )
    ''')
    
    return conn

@pytest.fixture
def service(db):
    """Create GroupService instance"""
    return GroupService(db)

@pytest.fixture
def test_data(db):
    """Create test data"""
    cursor = db.cursor()
    
    # Create test groups
    cursor.execute('INSERT INTO groups (name) VALUES (?)', ('Test Group',))
    group_id = cursor.lastrowid
    
    # Create test words
    test_words = [
        ('hola', 'hello'),
        ('adios', 'goodbye'),
        ('gracias', 'thank you')
    ]
    
    for spanish, english in test_words:
        cursor.execute(
            'INSERT INTO words (spanish, english) VALUES (?, ?)',
            (spanish, english)
        )
        word_id = cursor.lastrowid
        cursor.execute(
            'INSERT INTO word_groups (word_id, group_id) VALUES (?, ?)',
            (word_id, group_id)
        )
    
    db.commit()
    return {'group_id': group_id}

def test_get_group_words_raw(service, test_data):
    """Test getting raw words from a group"""
    words = service.get_group_words_raw(test_data['group_id'])
    
    assert words is not None
    assert len(words) == 3
    assert all(isinstance(w, Word) for w in words)
    assert any(w.spanish == 'hola' and w.english == 'hello' for w in words)

def test_get_group_words_raw_nonexistent_group(service):
    """Test getting words from non-existent group"""
    words = service.get_group_words_raw(999)
    assert words is None

def test_get_groups_pagination(service, test_data):
    """Test group pagination"""
    result = service.get_groups(page=1, per_page=10)
    
    assert result.current_page == 1
    assert len(result.items) == 1
    assert result.items[0]['group_name'] == 'Test Group'

def test_get_group_words_pagination(service, test_data):
    """Test word pagination"""
    result = service.get_group_words(
        group_id=test_data['group_id'],
        page=1,
        per_page=2
    )
    
    assert result is not None
    assert result.current_page == 1
    assert len(result.items) == 2
    assert result.total_pages == 2

def test_get_group_words_sorting(service, test_data):
    """Test word sorting"""
    result = service.get_group_words(
        group_id=test_data['group_id'],
        page=1,
        per_page=10,
        sort_by='spanish',
        order='asc'
    )
    
    assert result is not None
    words = [w['spanish'] for w in result.items]
    assert words == sorted(words) 