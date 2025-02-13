from typing import List, Optional, Dict
from dataclasses import dataclass
import sqlite3
from datetime import datetime, UTC

@dataclass
class StudySession:
    id: int
    group_id: int
    study_activity_id: int
    created_at: str
    group_name: str
    activity_name: str

class StudySessionService:
    def __init__(self, db_connection: sqlite3.Connection):
        self.db = db_connection
    
    def create_session(self, group_id: int, study_activity_id: int) -> Optional[StudySession]:
        """Create a new study session.
        
        Args:
            group_id: ID of the group to study
            study_activity_id: ID of the study activity
            
        Returns:
            StudySession if created successfully, None if group/activity not found
        """
        cursor = self.db.cursor()
        
        # Verify group exists
        cursor.execute('SELECT name FROM groups WHERE id = ?', (group_id,))
        group = cursor.fetchone()
        if not group:
            return None
            
        # Verify activity exists
        cursor.execute('SELECT name FROM study_activities WHERE id = ?', (study_activity_id,))
        activity = cursor.fetchone()
        if not activity:
            return None
            
        # Create session with UTC timestamp
        created_at = datetime.now(UTC).isoformat()
        cursor.execute('''
            INSERT INTO study_sessions (group_id, study_activity_id, created_at)
            VALUES (?, ?, ?)
        ''', (group_id, study_activity_id, created_at))
        
        session_id = cursor.lastrowid
        self.db.commit()
        
        return StudySession(
            id=session_id,
            group_id=group_id,
            study_activity_id=study_activity_id,
            created_at=created_at,
            group_name=group['name'],
            activity_name=activity['name']
        )
    
    def review_word(self, session_id: int, word_id: int, correct: bool) -> Optional[Dict]:
        """Record a word review in a study session.
        
        Args:
            session_id: ID of the study session
            word_id: ID of the word reviewed
            correct: Whether the answer was correct
            
        Returns:
            Review data if successful, None if session/word not found
        """
        cursor = self.db.cursor()
        
        # Verify session exists
        cursor.execute('SELECT id FROM study_sessions WHERE id = ?', (session_id,))
        if not cursor.fetchone():
            return None
            
        # Verify word exists
        cursor.execute('SELECT id FROM words WHERE id = ?', (word_id,))
        if not cursor.fetchone():
            return None
            
        # Record review with UTC timestamp
        created_at = datetime.now(UTC).isoformat()
        cursor.execute('''
            INSERT INTO word_review_items (
                study_session_id, word_id, correct, created_at
            ) VALUES (?, ?, ?, ?)
        ''', (session_id, word_id, correct, created_at))
        
        # Update word review counts
        cursor.execute('''
            INSERT OR REPLACE INTO word_reviews (word_id, correct_count, wrong_count)
            VALUES (
                ?,
                (SELECT COALESCE(SUM(correct = 1), 0) FROM word_review_items WHERE word_id = ?),
                (SELECT COALESCE(SUM(correct = 0), 0) FROM word_review_items WHERE word_id = ?)
            )
        ''', (word_id, word_id, word_id))
        
        self.db.commit()
        
        return {
            'success': True,
            'word_id': word_id,
            'study_session_id': session_id,
            'correct': correct,
            'created_at': created_at
        } 