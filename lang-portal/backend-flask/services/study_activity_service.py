from typing import List, Dict, Optional
from dataclasses import dataclass
import sqlite3

@dataclass
class StudyActivity:
    id: int
    name: str
    launch_url: str
    preview_url: str

class StudyActivityService:
    def __init__(self, db_connection: sqlite3.Connection):
        self.db = db_connection
    
    def get_all_activities(self) -> List[Dict]:
        """Get all study activities.
        
        Returns:
            List of activity dictionaries with id, name, launch_url, and preview_url
        """
        cursor = self.db.cursor()
        cursor.execute('''
            SELECT id, name, launch_url, preview_url
            FROM study_activities
            ORDER BY name
        ''')
        
        return [{
            'id': row['id'],
            'name': row['name'],
            'launch_url': row['launch_url'],
            'preview_url': row['preview_url']
        } for row in cursor.fetchall()]
    
    def get_activity(self, activity_id: int) -> Optional[Dict]:
        """Get a single study activity by ID.
        
        Args:
            activity_id: ID of the activity to fetch
            
        Returns:
            Activity dictionary if found, None if not found
        """
        cursor = self.db.cursor()
        cursor.execute('''
            SELECT id, name, launch_url, preview_url
            FROM study_activities
            WHERE id = ?
        ''', (activity_id,))
        
        row = cursor.fetchone()
        if not row:
            return None
            
        return {
            'id': row['id'],
            'name': row['name'],
            'launch_url': row['launch_url'],
            'preview_url': row['preview_url']
        }
    
    def create_activity(self, name: str, launch_url: str, preview_url: str) -> Dict:
        """Create a new study activity.
        
        Args:
            name: Name of the activity
            launch_url: URL of the activity
            preview_url: Preview URL of the activity
            
        Returns:
            Created activity dictionary
        """
        cursor = self.db.cursor()
        cursor.execute('''
            INSERT INTO study_activities (name, launch_url, preview_url)
            VALUES (?, ?, ?)
        ''', (name, launch_url, preview_url))
        
        activity_id = cursor.lastrowid
        self.db.commit()
        
        return {
            'id': activity_id,
            'name': name,
            'launch_url': launch_url,
            'preview_url': preview_url
        } 