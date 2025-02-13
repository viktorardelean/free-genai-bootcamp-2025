from typing import List, Optional, Dict, Tuple
from models.word import Word
from models.group import Group
import sqlite3
from dataclasses import dataclass
from datetime import datetime

@dataclass
class PaginatedResult:
    items: List[Dict]
    total_pages: int
    current_page: int
    total_items: int

class GroupService:
    def __init__(self, db_connection: sqlite3.Connection):
        self.db = db_connection
    
    def get_groups(self, page: int, per_page: int, sort_by: str = 'name', order: str = 'asc') -> PaginatedResult:
        """Get paginated list of groups with word counts."""
        cursor = self.db.cursor()
        offset = (page - 1) * per_page
        
        # Validate sort parameters
        valid_columns = ['name', 'words_count']
        if sort_by not in valid_columns:
            sort_by = 'name'
        if order not in ['asc', 'desc']:
            order = 'asc'
            
        # Get total count
        cursor.execute('SELECT COUNT(*) FROM groups')
        total_groups = cursor.fetchone()[0]
        total_pages = (total_groups + per_page - 1) // per_page
        
        # Get groups with word counts
        cursor.execute(f'''
            SELECT 
                g.id,
                g.name,
                COALESCE(g.words_count, 
                    (SELECT COUNT(*) 
                     FROM word_groups wg 
                     WHERE wg.group_id = g.id)
                ) as word_count
            FROM groups g
            ORDER BY {sort_by} {order}
            LIMIT ? OFFSET ?
        ''', (per_page, offset))
        
        groups = [{
            "id": row["id"],
            "group_name": row["name"],
            "word_count": row["word_count"]
        } for row in cursor.fetchall()]
        
        return PaginatedResult(
            items=groups,
            total_pages=total_pages,
            current_page=page,
            total_items=total_groups
        )
    
    def get_group_words(self, group_id: int, page: int, per_page: int, 
                       sort_by: str = 'spanish', order: str = 'asc') -> Optional[PaginatedResult]:
        """Get paginated list of words in a group."""
        cursor = self.db.cursor()
        offset = (page - 1) * per_page
        
        # Check if group exists
        cursor.execute('SELECT name FROM groups WHERE id = ?', (group_id,))
        if not cursor.fetchone():
            return None
            
        # Validate sort parameters
        valid_columns = ['spanish', 'english']
        if sort_by not in valid_columns:
            sort_by = 'spanish'
        if order not in ['asc', 'desc']:
            order = 'asc'
            
        # Get total count
        cursor.execute('''
            SELECT COUNT(*) 
            FROM word_groups 
            WHERE group_id = ?
        ''', (group_id,))
        total_words = cursor.fetchone()[0]
        total_pages = (total_words + per_page - 1) // per_page
        
        # Get words
        cursor.execute(f'''
            SELECT w.* 
            FROM words w
            JOIN word_groups wg ON w.id = wg.word_id
            WHERE wg.group_id = ?
            ORDER BY w.{sort_by} COLLATE NOCASE {order}
            LIMIT ? OFFSET ?
        ''', (group_id, per_page, offset))
        
        words = [{
            "id": row["id"],
            "spanish": row["spanish"],
            "english": row["english"]
        } for row in cursor.fetchall()]
        
        return PaginatedResult(
            items=words,
            total_pages=total_pages,
            current_page=page,
            total_items=total_words
        )
    
    def get_group_study_sessions(self, group_id: int, page: int, per_page: int,
                               sort_by: str = 'created_at', order: str = 'desc') -> Optional[PaginatedResult]:
        """Get paginated list of study sessions for a group.
        
        Args:
            group_id: ID of the group
            page: Current page number
            per_page: Items per page
            sort_by: Column to sort by
            order: Sort order ('asc' or 'desc')
            
        Returns:
            PaginatedResult if group exists, None if not found
        """
        cursor = self.db.cursor()
        offset = (page - 1) * per_page
        
        # Map frontend sort keys to database columns
        sort_mapping = {
            'startTime': 'created_at',
            'endTime': 'last_activity_time',
            'activityName': 'a.name',
            'groupName': 'g.name',
            'reviewItemsCount': 'review_count'
        }
        sort_column = sort_mapping.get(sort_by, 'created_at')
        
        # Get total count
        cursor.execute('''
            SELECT COUNT(*)
            FROM study_sessions
            WHERE group_id = ?
        ''', (group_id,))
        total_sessions = cursor.fetchone()[0]
        total_pages = (total_sessions + per_page - 1) // per_page
        
        # Get study sessions
        cursor.execute(f'''
            SELECT 
                s.id,
                s.group_id,
                s.study_activity_id,
                s.created_at as start_time,
                (
                    SELECT MAX(created_at)
                    FROM word_review_items
                    WHERE study_session_id = s.id
                ) as last_activity_time,
                a.name as activity_name,
                g.name as group_name,
                (
                    SELECT COUNT(*)
                    FROM word_review_items
                    WHERE study_session_id = s.id
                ) as review_count
            FROM study_sessions s
            JOIN study_activities a ON s.study_activity_id = a.id
            JOIN groups g ON s.group_id = g.id
            WHERE s.group_id = ?
            ORDER BY {sort_column} {order}
            LIMIT ? OFFSET ?
        ''', (group_id, per_page, offset))
        
        sessions = [{
            "id": row["id"],
            "group_id": row["group_id"],
            "study_activity_id": row["study_activity_id"],
            "start_time": row["start_time"],
            "last_activity_time": row["last_activity_time"],
            "activity_name": row["activity_name"],
            "group_name": row["group_name"],
            "review_count": row["review_count"]
        } for row in cursor.fetchall()]
        
        return PaginatedResult(
            items=sessions,
            total_pages=total_pages,
            current_page=page,
            total_items=total_sessions
        )

    def get_group_words_raw(self, group_id: int) -> Optional[List[Word]]:
        """Get raw words for a group without study statistics.
        
        Args:
            group_id: The group ID to fetch words for
            
        Returns:
            List of Word objects if group exists, None if group not found
            
        Raises:
            Exception: If database error occurs
        """
        cursor = self.db.cursor()
        
        # Check if group exists
        cursor.execute('SELECT id FROM groups WHERE id = ?', (group_id,))
        if not cursor.fetchone():
            return None
        
        # Get words for group without study statistics
        cursor.execute('''
            SELECT DISTINCT
                w.id,
                w.spanish,
                w.english
            FROM words w
            JOIN word_groups wg ON wg.word_id = w.id
            WHERE wg.group_id = ?
            ORDER BY w.spanish COLLATE NOCASE
        ''', (group_id,))
        
        rows = cursor.fetchall()
        return [
            Word(
                id=row['id'],
                spanish=row['spanish'],
                english=row['english']
            )
            for row in rows
        ] 