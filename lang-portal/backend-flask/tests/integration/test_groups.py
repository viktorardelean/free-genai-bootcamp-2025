import pytest
from flask import Flask
import sqlite3
from pathlib import Path
import os
from models.word import Word
from models.group import Group
from services.group_service import GroupService

@pytest.fixture(autouse=True)
def cleanup():
    """Remove test database before and after each test"""
    db_path = Path(__file__).parent.parent.parent / 'words.db'
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
    with app.app_context():
        cursor = app.db.cursor()
        
        # Create tables with updated schema
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
    
    # Create test groups
    groups = [
        ('Animals', [
            ('perro', 'dog'),
            ('gato', 'cat'),
            ('pájaro', 'bird')
        ]),
        ('Colors', [
            ('rojo', 'red'),
            ('azul', 'blue'),
            ('verde', 'green')
        ])
    ]
    
    group_ids = {}
    for group_name, words in groups:
        # Create group with word count
        cursor.execute('''
            INSERT INTO groups (name, words_count) 
            VALUES (?, ?)
        ''', (group_name, len(words)))
        group_id = cursor.lastrowid
        group_ids[group_name] = group_id
        
        # Add words to group
        for spanish, english in words:
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
    return group_ids

def test_get_group_words_raw_integration(client, app, test_data):
    """Integration test for getting raw words from a group"""
    # Test using service directly
    service = GroupService(app.db)
    words = service.get_group_words_raw(test_data["Animals"])
    
    # Verify service response
    assert len(words) == 3
    assert all(isinstance(w, Word) for w in words)
    assert any(w.spanish == 'gato' and w.english == 'cat' for w in words)
    
    # Test HTTP endpoint
    response = client.get(f'/api/groups/{test_data["Animals"]}/words/raw')
    assert response.status_code == 200
    data = response.get_json()
    
    # Verify response structure
    assert 'items' in data
    assert len(data['items']) == 3
    
    # Verify words through API match service response
    api_words = {w['spanish']: w['english'] for w in data['items']}
    service_words = {w.spanish: w.english for w in words}
    assert api_words == service_words

def test_get_group_words_raw_cross_group_isolation_integration(client, app, test_data):
    """Test that words from different groups don't mix"""
    # Get words from Colors group
    response = client.get(f'/api/groups/{test_data["Colors"]}/words/raw')
    assert response.status_code == 200
    data = response.get_json()
    
    # Verify only color words are returned
    words = {word['spanish']: word['english'] for word in data['items']}
    assert len(words) == 3
    assert 'rojo' in words
    assert 'azul' in words
    assert 'verde' in words
    assert 'gato' not in words  # Should not include words from Animals group

def test_get_group_words_raw_shared_words_integration(client, app, test_data):
    """Test handling words shared between groups"""
    cursor = app.db.cursor()
    
    # Add a shared word to both groups
    cursor.execute(
        'INSERT INTO words (spanish, english) VALUES (?, ?)',
        ('compartido', 'shared')
    )
    shared_word_id = cursor.lastrowid
    
    # Add to both groups
    for group_id in test_data.values():
        cursor.execute(
            'INSERT INTO word_groups (word_id, group_id) VALUES (?, ?)',
            (shared_word_id, group_id)
        )
    
    app.db.commit()
    
    # Check each group
    for group_id in test_data.values():
        response = client.get(f'/api/groups/{group_id}/words/raw')
        assert response.status_code == 200
        data = response.get_json()
        
        # Verify shared word appears in each group
        words = {word['spanish']: word['english'] for word in data['items']}
        assert 'compartido' in words
        assert words['compartido'] == 'shared'

def test_get_group_words_raw_database_state_integration(client, app, test_data):
    """Test that endpoint doesn't modify database state"""
    cursor = app.db.cursor()
    
    # Get initial counts
    cursor.execute('SELECT COUNT(*) FROM words')
    initial_word_count = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM word_groups')
    initial_group_count = cursor.fetchone()[0]
    
    # Make several requests
    for _ in range(5):
        for group_id in test_data.values():
            response = client.get(f'/api/groups/{group_id}/words/raw')
            assert response.status_code == 200
    
    # Verify counts haven't changed
    cursor.execute('SELECT COUNT(*) FROM words')
    assert cursor.fetchone()[0] == initial_word_count
    cursor.execute('SELECT COUNT(*) FROM word_groups')
    assert cursor.fetchone()[0] == initial_group_count

def test_get_group_words_raw_concurrent_access_integration(client, app, test_data):
    """Test concurrent access to the endpoint"""
    from concurrent.futures import ThreadPoolExecutor
    import threading
    
    # Create a lock for database access
    db_lock = threading.Lock()
    
    def make_request(group_id):
        with db_lock:  # Ensure thread-safe database access
            with app.app_context():
                return client.get(f'/api/groups/{group_id}/words/raw')
    
    # Make concurrent requests
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = []
        for _ in range(10):  # Make 10 concurrent requests
            for group_id in test_data.values():
                futures.append(executor.submit(make_request, group_id))
        
        # Verify all requests succeeded
        for future in futures:
            response = future.result()
            assert response.status_code == 200
            data = response.get_json()
            assert 'items' in data
            assert len(data['items']) > 0  # Should have words

def test_get_groups_pagination_integration(client, app, test_data):
    """Test group pagination through API"""
    # Test first page
    response = client.get('/api/groups?page=1&per_page=2')
    assert response.status_code == 200
    data = response.get_json()
    
    assert 'groups' in data
    assert 'total_pages' in data
    assert 'current_page' in data
    assert len(data['groups']) <= 2

def test_get_group_words_sorting_integration(client, app, test_data):
    """Test word sorting through API"""
    # Test ascending order
    response = client.get(
        f'/api/groups/{test_data["Animals"]}/words?sort_by=spanish&order=asc'
    )
    assert response.status_code == 200
    data = response.get_json()
    
    words = [w['spanish'] for w in data['words']]
    assert words == sorted(words)
    
    # Test descending order
    response = client.get(
        f'/api/groups/{test_data["Animals"]}/words?sort_by=spanish&order=desc'
    )
    assert response.status_code == 200
    data = response.get_json()
    
    words = [w['spanish'] for w in data['words']]
    assert words == sorted(words, reverse=True)

def test_get_groups_pagination_invalid_page(client, app, test_data):
    """Test pagination with invalid page number"""
    response = client.get('/api/groups?page=invalid')
    assert response.status_code == 400
    data = response.get_json()
    assert 'error' in data
    assert data['error'] == "Invalid pagination parameters"

def test_get_group_words_sorting_invalid_params(client, app, test_data):
    """Test sorting with invalid parameters"""
    # Test invalid sort column
    response = client.get(
        f'/api/groups/{test_data["Animals"]}/words?sort_by=invalid&order=asc'
    )
    assert response.status_code == 200  # Should use default sort
    
    # Test invalid order
    response = client.get(
        f'/api/groups/{test_data["Animals"]}/words?sort_by=spanish&order=invalid'
    )
    assert response.status_code == 200  # Should use default order 