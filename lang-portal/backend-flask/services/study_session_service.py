from typing import List, Optional, Dict
from dataclasses import dataclass
import sqlite3
from datetime import datetime, UTC
import traceback
import logging

# Configure logging
logger = logging.getLogger(__name__)

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
    
    def submit_word_review(self, session_id: int, word_id: int, correct: bool) -> bool:
        """Submit a word review for a study session"""
        try:
            cursor = self.db.cursor()
            cursor.execute('''
                INSERT INTO word_review_items (study_session_id, word_id, correct, created_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ''', (session_id, word_id, correct))
            self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Error submitting word review: {e}")
            return False

    def review_word(self, session_id: int, word_id: int, correct: bool):
        """Create a word review for a study session"""
        try:
            cursor = self.db.cursor()
            
            # First verify session exists
            cursor.execute('SELECT id FROM study_sessions WHERE id = ?', (session_id,))
            session = cursor.fetchone()
            if not session:
                logger.error(f"Session {session_id} not found")
                return None
            
            # Then verify word exists
            cursor.execute('SELECT id FROM words WHERE id = ?', (word_id,))
            word = cursor.fetchone()
            if not word:
                logger.error(f"Word {word_id} not found")
                return None
            
            # Create the review with UTC timestamp
            created_at = datetime.now(UTC).isoformat()
            cursor.execute('''
                INSERT INTO word_review_items (
                    study_session_id,
                    word_id,
                    correct,
                    created_at
                ) VALUES (?, ?, ?, ?)
            ''', (session_id, word_id, correct, created_at))
            
            # Update statistics in word_review_items_stats table
            cursor.execute('''
                INSERT OR REPLACE INTO word_review_items_stats (
                    word_id,
                    correct_count,
                    wrong_count,
                    last_reviewed
                ) VALUES (
                    ?,
                    (SELECT COUNT(*) FROM word_review_items WHERE word_id = ? AND correct = 1),
                    (SELECT COUNT(*) FROM word_review_items WHERE word_id = ? AND correct = 0),
                    CURRENT_TIMESTAMP
                )
            ''', (word_id, word_id, word_id))
            
            self.db.commit()
            
            return {
                'success': True,
                'id': cursor.lastrowid,
                'study_session_id': session_id,
                'word_id': word_id,
                'correct': correct,
                'created_at': created_at
            }
            
        except Exception as e:
            logger.error(f"Error in review_word: {str(e)}")
            logger.error(traceback.format_exc())
            raise 