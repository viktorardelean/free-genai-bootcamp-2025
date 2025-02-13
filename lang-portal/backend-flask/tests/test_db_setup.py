import pytest
import sqlite3
from pathlib import Path
from db.init_db import init_db, main as init_and_seed
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

def test_database_initialization():
    """Test that database is created and migrations run successfully"""
    # Run initialization
    init_db()
    
    # Connect to database
    db_path = Path(__file__).parent.parent / 'words.db'
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Check tables exist
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row['name'] for row in cursor.fetchall()}
    
    expected_tables = {
        'groups',
        'words',
        'word_groups',
        'study_activities',
        'study_sessions',
        'word_review_items'
    }
    
    assert expected_tables.issubset(tables), "Not all expected tables were created"

def test_seeding():
    """Test that seed data is properly loaded"""
    # Run full initialization and seeding
    init_and_seed()
    
    # Connect to database
    db_path = Path(__file__).parent.parent / 'words.db'
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Check groups were created
    cursor.execute("SELECT name FROM groups")
    groups = {row['name'] for row in cursor.fetchall()}
    expected_groups = {'Animals', 'Colors', 'Numbers', 'Food', 'Family'}
    assert expected_groups == groups, "Not all expected groups were created"
    
    # Check words were added
    cursor.execute("""
        SELECT g.name as group_name, COUNT(w.id) as word_count
        FROM groups g
        JOIN word_groups wg ON wg.group_id = g.id
        JOIN words w ON w.id = wg.word_id
        GROUP BY g.name
    """)
    word_counts = {row['group_name']: row['word_count'] for row in cursor.fetchall()}
    
    # Verify each group has words
    assert word_counts['Animals'] == 3, "Animals group should have 3 words"
    assert word_counts['Colors'] == 6, "Colors group should have 6 words"
    assert word_counts['Numbers'] == 5, "Numbers group should have 5 words"
    assert word_counts['Food'] == 5, "Food group should have 5 words"
    assert word_counts['Family'] == 6, "Family group should have 6 words"
    
    # Check study activities were added
    cursor.execute("SELECT name FROM study_activities")
    activities = {row['name'] for row in cursor.fetchall()}
    expected_activities = {'Flashcards', 'Multiple Choice', 'Spelling', 'Translation'}
    assert expected_activities == activities, "Not all study activities were created"

def test_word_group_relationships():
    """Test that words are properly associated with groups"""
    # Initialize and seed database first
    init_and_seed()
    
    db_path = Path(__file__).parent.parent / 'words.db'
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Check a few specific words
    cursor.execute("""
        SELECT w.spanish, w.english, g.name as group_name
        FROM words w
        JOIN word_groups wg ON wg.word_id = w.id
        JOIN groups g ON g.id = wg.group_id
        WHERE w.spanish IN ('gato', 'rojo', 'uno', 'pan', 'madre')
    """)
    
    words = {row['spanish']: row['group_name'] for row in cursor.fetchall()}
    assert words['gato'] == 'Animals'
    assert words['rojo'] == 'Colors'
    assert words['uno'] == 'Numbers'
    assert words['pan'] == 'Food'
    assert words['madre'] == 'Family' 