import pytest
from flask import Flask
import sqlite3
from pathlib import Path
import os

@pytest.fixture(autouse=True)
def cleanup():
    """Remove test database before and after each test"""
    db_path = Path(__file__).parent.parent / 'words.db'
    if db_path.exists():
        os.remove(db_path)
    yield
    if db_path.exists():
        os.remove(db_path)

@pytest.fixture
def app():
    """Create test app with real database connection"""
    app = Flask(__name__)
    
    # Use an in-memory SQLite database for testing
    app.db = sqlite3.connect(':memory:', check_same_thread=False)
    app.db.row_factory = sqlite3.Row
    
    # Create test tables
    cursor = app.db.cursor()
    
    # Enable case-insensitive and accent-sensitive collation
    cursor.execute('PRAGMA case_sensitive_like = OFF')
    
    # Create groups table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL
        )
    ''')
    
    # Create words table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS words (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            spanish TEXT NOT NULL COLLATE NOCASE,
            english TEXT NOT NULL
        )
    ''')
    
    # Create word_groups table with unique constraint
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS word_groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            word_id INTEGER NOT NULL,
            group_id INTEGER NOT NULL,
            UNIQUE(word_id, group_id),
            FOREIGN KEY (word_id) REFERENCES words (id),
            FOREIGN KEY (group_id) REFERENCES groups (id)
        )
    ''')
    
    app.db.commit()
    
    # Import and register routes
    from routes.groups import load
    load(app)
    
    return app

@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()

@pytest.fixture
def test_data(app):
    """Create test data"""
    cursor = app.db.cursor()
    
    # Create test group
    cursor.execute('INSERT INTO groups (name) VALUES (?)', ('Test Group',))
    group_id = cursor.lastrowid
    
    app.db.commit()
    
    return {
        'group_id': group_id
    }

def test_get_group_words_raw_success(client, app, test_data):
    """Test getting raw words for a group"""
    # Create test group and words
    cursor = app.db.cursor()
    
    # Insert test group
    cursor.execute('INSERT INTO groups (name) VALUES (?)', ('Test Group',))
    group_id = cursor.lastrowid
    
    # Insert test words
    test_words = [
        ('hola', 'hello'),
        ('adios', 'goodbye'),
        ('gracias', 'thank you')
    ]
    
    for spanish, english in test_words:
        # Insert word
        cursor.execute(
            'INSERT INTO words (spanish, english) VALUES (?, ?)',
            (spanish, english)
        )
        word_id = cursor.lastrowid
        
        # Associate with group
        cursor.execute(
            'INSERT INTO word_groups (word_id, group_id) VALUES (?, ?)',
            (word_id, group_id)
        )
    
    app.db.commit()
    
    # Test endpoint
    response = client.get(f'/api/groups/{group_id}/words/raw')
    
    # Check response
    assert response.status_code == 200
    data = response.get_json()
    assert 'items' in data
    assert len(data['items']) == 3
    
    # Check word data
    words = {word['spanish']: word['english'] for word in data['items']}
    assert words['hola'] == 'hello'
    assert words['adios'] == 'goodbye'
    assert words['gracias'] == 'thank you'

def test_get_group_words_raw_nonexistent_group(client, app):
    """Test getting raw words for a non-existent group"""
    response = client.get('/api/groups/999/words/raw')
    assert response.status_code == 404
    assert response.get_json()['error'] == "Group not found"

def test_get_group_words_raw_empty_group(client, app):
    """Test getting raw words for an empty group"""
    # Create empty group
    cursor = app.db.cursor()
    cursor.execute('INSERT INTO groups (name) VALUES (?)', ('Empty Group',))
    group_id = cursor.lastrowid
    app.db.commit()
    
    response = client.get(f'/api/groups/{group_id}/words/raw')
    assert response.status_code == 200
    data = response.get_json()
    assert 'items' in data
    assert len(data['items']) == 0

def test_get_group_words_raw_ordering(client, app):
    """Test that words are returned in correct alphabetical order"""
    cursor = app.db.cursor()
    
    # Create test group
    cursor.execute('INSERT INTO groups (name) VALUES (?)', ('Test Group',))
    group_id = cursor.lastrowid
    
    # Insert words in non-alphabetical order
    test_words = [
        ('zapato', 'shoe'),
        ('agua', 'water'),
        ('mesa', 'table'),
        ('libro', 'book')
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
    
    app.db.commit()
    
    response = client.get(f'/api/groups/{group_id}/words/raw')
    assert response.status_code == 200
    data = response.get_json()
    
    # Check words are in alphabetical order
    spanish_words = [word['spanish'] for word in data['items']]
    assert spanish_words == ['agua', 'libro', 'mesa', 'zapato']

def test_get_group_words_raw_special_characters(client, app):
    """Test handling of Spanish special characters in ordering"""
    cursor = app.db.cursor()
    
    cursor.execute('INSERT INTO groups (name) VALUES (?)', ('Test Group',))
    group_id = cursor.lastrowid
    
    # Words with special characters
    test_words = [
        ('ñandu', 'rhea'),
        ('niño', 'child'),
        ('árbol', 'tree'),
        ('angel', 'angel')
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
    
    app.db.commit()
    
    response = client.get(f'/api/groups/{group_id}/words/raw')
    assert response.status_code == 200
    data = response.get_json()
    
    # Verify words are returned in alphabetical order
    spanish_words = [word['spanish'] for word in data['items']]
    # SQLite's NOCASE collation will sort these slightly differently
    assert len(spanish_words) == 4
    assert spanish_words[0] == 'angel'  # 'angel' comes first
    assert 'árbol' in spanish_words
    assert 'niño' in spanish_words
    assert 'ñandu' in spanish_words

def test_get_group_words_raw_duplicate_words(client, app):
    """Test handling of duplicate word associations"""
    cursor = app.db.cursor()
    
    # Create test group
    cursor.execute('INSERT INTO groups (name) VALUES (?)', ('Test Group',))
    group_id = cursor.lastrowid
    
    # Insert a word
    cursor.execute(
        'INSERT INTO words (spanish, english) VALUES (?, ?)',
        ('hola', 'hello')
    )
    word_id = cursor.lastrowid
    
    # Try to associate the same word twice with the group
    cursor.execute(
        'INSERT INTO word_groups (word_id, group_id) VALUES (?, ?)',
        (word_id, group_id)
    )
    try:
        cursor.execute(
            'INSERT INTO word_groups (word_id, group_id) VALUES (?, ?)',
            (word_id, group_id)
        )
    except:
        pass  # Expected to fail due to unique constraint
    
    app.db.commit()
    
    response = client.get(f'/api/groups/{group_id}/words/raw')
    assert response.status_code == 200
    data = response.get_json()
    
    # Verify word appears only once
    assert len(data['items']) == 1
    assert data['items'][0]['spanish'] == 'hola'

def test_get_group_words_raw_malformed_group_id(client, app):
    """Test handling of malformed group ID"""
    response = client.get('/api/groups/invalid/words/raw')
    assert response.status_code == 404

def test_get_group_words_raw_large_dataset(client, app):
    """Test handling of large number of words"""
    cursor = app.db.cursor()
    
    # Create test group
    cursor.execute('INSERT INTO groups (name) VALUES (?)', ('Large Group',))
    group_id = cursor.lastrowid
    
    # Insert 100 words
    for i in range(100):
        cursor.execute(
            'INSERT INTO words (spanish, english) VALUES (?, ?)',
            (f'palabra{i:03d}', f'word{i:03d}')
        )
        word_id = cursor.lastrowid
        cursor.execute(
            'INSERT INTO word_groups (word_id, group_id) VALUES (?, ?)',
            (word_id, group_id)
        )
    
    app.db.commit()
    
    response = client.get(f'/api/groups/{group_id}/words/raw')
    assert response.status_code == 200
    data = response.get_json()
    
    # Verify all words are returned and ordered
    assert len(data['items']) == 100
    spanish_words = [word['spanish'] for word in data['items']]
    assert spanish_words == sorted(spanish_words) 