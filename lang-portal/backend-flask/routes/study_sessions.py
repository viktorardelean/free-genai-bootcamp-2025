from flask import request, jsonify, g
from flask_cors import cross_origin
from datetime import datetime
import math
from contextlib import contextmanager

# Constants for error messages
ERROR_MESSAGES = {
    'MISSING_FIELDS': "Missing required fields: group_id or study_activity_id",
    'INVALID_TYPES': "group_id and study_activity_id must be integers",
    'GROUP_NOT_FOUND': "Group not found",
    'ACTIVITY_NOT_FOUND': "Study activity not found",
    'CREATE_FAILED': "Failed to create session",
    'MISSING_CORRECT': "Missing required field: correct",
    'INVALID_CORRECT': "Field 'correct' must be a boolean",
    'SESSION_NOT_FOUND': "Study session not found",
    'WORD_NOT_FOUND': "Word not found",
    'REVIEW_CREATE_FAILED': "Failed to create review",
    'INVALID_JSON': "Invalid JSON payload",
    'INVALID_CONTENT_TYPE': "Content-Type must be application/json"
}

@contextmanager
def transaction(db):
    """Context manager for database transactions.
    
    Automatically handles commit/rollback based on whether
    an exception occurs in the wrapped code.
    
    Args:
        db: Database connection object
        
    Yields:
        None
    """
    try:
        yield
        db.commit()
    except Exception:
        db.rollback()
        raise

def load(app):
  @app.route('/api/study-sessions', methods=['POST'])
  @cross_origin()
  def create_study_session() -> tuple:
    """Create a new study session.
    
    Accepts JSON payload with group_id and study_activity_id.
    Validates inputs, creates session, and returns the created session data.
    
    Returns:
        tuple: (JSON response, HTTP status code)
    """
    try:
      data = request.get_json()
      group_id = data.get('group_id')
      study_activity_id = data.get('study_activity_id')

      # Validate required fields
      if group_id is None or study_activity_id is None:
        return jsonify({"error": ERROR_MESSAGES['MISSING_FIELDS']}), 400

      # Validate types
      if not isinstance(group_id, int) or not isinstance(study_activity_id, int):
        return jsonify({"error": ERROR_MESSAGES['INVALID_TYPES']}), 400

      cursor = app.db.cursor()

      # Validate foreign keys exist
      cursor.execute('SELECT id FROM groups WHERE id = ?', (group_id,))
      if not cursor.fetchone():
        return jsonify({"error": ERROR_MESSAGES['GROUP_NOT_FOUND']}), 404

      cursor.execute('SELECT id FROM study_activities WHERE id = ?', (study_activity_id,))
      if not cursor.fetchone():
        return jsonify({"error": ERROR_MESSAGES['ACTIVITY_NOT_FOUND']}), 404

      with transaction(app.db):
        created_at = datetime.now()

        # Insert the new study session
        insert_stmt = '''
          INSERT INTO study_sessions (group_id, study_activity_id, created_at)
          VALUES (?, ?, ?)
        '''
        cursor.execute(insert_stmt, (group_id, study_activity_id, created_at))
        
        new_session_id = cursor.lastrowid

        # Fetch the newly created session
        cursor.execute('''
          SELECT 
            ss.id,
            ss.group_id,
            g.name as group_name,
            sa.id as activity_id,
            sa.name as activity_name,
            ss.created_at,
            COUNT(wri.id) as review_items_count
          FROM study_sessions ss
          JOIN groups g ON g.id = ss.group_id
          JOIN study_activities sa ON sa.id = ss.study_activity_id
          LEFT JOIN word_review_items wri ON wri.study_session_id = ss.id
          WHERE ss.id = ?
          GROUP BY ss.id
        ''', (new_session_id,))
        
        session = cursor.fetchone()
        
        # Verify session was created and fetched
        if not session:
          raise Exception(ERROR_MESSAGES['CREATE_FAILED'])

        response = {
          'id': session['id'],
          'group_id': session['group_id'],
          'group_name': session['group_name'],
          'activity_id': session['activity_id'],
          'activity_name': session['activity_name'],
          'start_time': session['created_at'],
          'end_time': session['created_at'],
          'review_items_count': session['review_items_count']
        }
        
        return jsonify(response), 201

    except Exception as e:
      return jsonify({"error": str(e)}), 500

  @app.route('/api/study-sessions', methods=['GET'])
  @cross_origin()
  def get_study_sessions():
    try:
      cursor = app.db.cursor()
      
      # Get pagination parameters
      page = request.args.get('page', 1, type=int)
      per_page = request.args.get('per_page', 10, type=int)
      offset = (page - 1) * per_page

      # Get total count
      cursor.execute('''
        SELECT COUNT(*) as count 
        FROM study_sessions ss
        JOIN groups g ON g.id = ss.group_id
        JOIN study_activities sa ON sa.id = ss.study_activity_id
      ''')
      total_count = cursor.fetchone()['count']

      # Get paginated sessions
      cursor.execute('''
        SELECT 
          ss.id,
          ss.group_id,
          g.name as group_name,
          sa.id as activity_id,
          sa.name as activity_name,
          ss.created_at,
          COUNT(wri.id) as review_items_count
        FROM study_sessions ss
        JOIN groups g ON g.id = ss.group_id
        JOIN study_activities sa ON sa.id = ss.study_activity_id
        LEFT JOIN word_review_items wri ON wri.study_session_id = ss.id
        GROUP BY ss.id
        ORDER BY ss.created_at DESC
        LIMIT ? OFFSET ?
      ''', (per_page, offset))
      sessions = cursor.fetchall()

      return jsonify({
        'items': [{
          'id': session['id'],
          'group_id': session['group_id'],
          'group_name': session['group_name'],
          'activity_id': session['activity_id'],
          'activity_name': session['activity_name'],
          'start_time': session['created_at'],
          'end_time': session['created_at'],  # For now, just use the same time since we don't track end time
          'review_items_count': session['review_items_count']
        } for session in sessions],
        'total': total_count,
        'page': page,
        'per_page': per_page,
        'total_pages': math.ceil(total_count / per_page)
      })
    except Exception as e:
      return jsonify({"error": str(e)}), 500

  @app.route('/api/study-sessions/<id>', methods=['GET'])
  @cross_origin()
  def get_study_session(id):
    try:
      cursor = app.db.cursor()
      
      # Get session details
      cursor.execute('''
        SELECT 
          ss.id,
          ss.group_id,
          g.name as group_name,
          sa.id as activity_id,
          sa.name as activity_name,
          ss.created_at,
          COUNT(wri.id) as review_items_count
        FROM study_sessions ss
        JOIN groups g ON g.id = ss.group_id
        JOIN study_activities sa ON sa.id = ss.study_activity_id
        LEFT JOIN word_review_items wri ON wri.study_session_id = ss.id
        WHERE ss.id = ?
        GROUP BY ss.id
      ''', (id,))
      
      session = cursor.fetchone()
      if not session:
        return jsonify({"error": "Study session not found"}), 404

      # Get pagination parameters
      page = request.args.get('page', 1, type=int)
      per_page = request.args.get('per_page', 10, type=int)
      offset = (page - 1) * per_page

      # Get the words reviewed in this session with their review status
      cursor.execute('''
        SELECT 
          w.*,
          COALESCE(SUM(CASE WHEN wri.correct = 1 THEN 1 ELSE 0 END), 0) as session_correct_count,
          COALESCE(SUM(CASE WHEN wri.correct = 0 THEN 1 ELSE 0 END), 0) as session_wrong_count
        FROM words w
        JOIN word_review_items wri ON wri.word_id = w.id
        WHERE wri.study_session_id = ?
        GROUP BY w.id
        ORDER BY w.spanish
        LIMIT ? OFFSET ?
      ''', (id, per_page, offset))
      
      words = cursor.fetchall()

      # Get total count of words
      cursor.execute('''
        SELECT COUNT(DISTINCT w.id) as count
        FROM words w
        JOIN word_review_items wri ON wri.word_id = w.id
        WHERE wri.study_session_id = ?
      ''', (id,))
      
      total_count = cursor.fetchone()['count']

      return jsonify({
        'session': {
          'id': session['id'],
          'group_id': session['group_id'],
          'group_name': session['group_name'],
          'activity_id': session['activity_id'],
          'activity_name': session['activity_name'],
          'start_time': session['created_at'],
          'end_time': session['created_at'],  # For now, just use the same time
          'review_items_count': session['review_items_count']
        },
        'words': [{
          'id': word['id'],
          'spanish': word['spanish'],
          'english': word['english'],
          'correct_count': word['session_correct_count'],
          'wrong_count': word['session_wrong_count']
        } for word in words],
        'total': total_count,
        'page': page,
        'per_page': per_page,
        'total_pages': math.ceil(total_count / per_page)
      })
    except Exception as e:
      return jsonify({"error": str(e)}), 500

  @app.route('/api/study-sessions/<int:id>/words/<int:word_id>/review', methods=['POST'])
  @cross_origin()
  def review_word_in_session(id, word_id):
    """Create a word review for a study session."""
    try:
        # Check content type
        if not request.is_json:
            return jsonify({"error": ERROR_MESSAGES['INVALID_CONTENT_TYPE']}), 400

        try:
            data = request.get_json()
        except Exception:
            return jsonify({"error": ERROR_MESSAGES['INVALID_JSON']}), 400

        if data is None:
            return jsonify({"error": ERROR_MESSAGES['INVALID_JSON']}), 400

        correct = data.get('correct')

        # Validate correct field exists and is boolean
        if correct is None:
            return jsonify({"error": ERROR_MESSAGES['MISSING_CORRECT']}), 400
        if not isinstance(correct, bool):
            return jsonify({"error": ERROR_MESSAGES['INVALID_CORRECT']}), 400

        cursor = app.db.cursor()

        # Check if study session exists
        cursor.execute('SELECT id FROM study_sessions WHERE id = ?', (id,))
        if not cursor.fetchone():
            return jsonify({"error": ERROR_MESSAGES['SESSION_NOT_FOUND']}), 404

        # Check if word exists
        cursor.execute('SELECT id FROM words WHERE id = ?', (word_id,))
        if not cursor.fetchone():
            return jsonify({"error": ERROR_MESSAGES['WORD_NOT_FOUND']}), 404

        with transaction(app.db):
            created_at = datetime.now()
            
            # Insert the review
            insert_stmt = '''
                INSERT INTO word_review_items (study_session_id, word_id, correct, created_at)
                VALUES (?, ?, ?, ?)
            '''
            cursor.execute(insert_stmt, (id, word_id, correct, created_at))
            review_id = cursor.lastrowid

            # Fetch the created review with related data
            cursor.execute('''
                SELECT 
                    wri.id,
                    wri.study_session_id,
                    wri.word_id,
                    wri.correct,
                    wri.created_at,
                    w.spanish,
                    w.english
                FROM word_review_items wri
                JOIN words w ON w.id = wri.word_id
                WHERE wri.id = ?
            ''', (review_id,))
            
            review = cursor.fetchone()
            
            if not review:
                raise Exception(ERROR_MESSAGES['REVIEW_CREATE_FAILED'])
            
            response = {
                'id': review['id'],
                'study_session_id': review['study_session_id'],
                'word_id': review['word_id'],
                'word_spanish': review['spanish'],
                'word_english': review['english'],
                'correct': bool(review['correct']),
                'created_at': review['created_at']
            }
            
            return jsonify(response), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500

  @app.route('/api/study-sessions/reset', methods=['POST'])
  @cross_origin()
  def reset_study_sessions():
    try:
      cursor = app.db.cursor()
      
      # First delete all word review items since they have foreign key constraints
      cursor.execute('DELETE FROM word_review_items')
      
      # Then delete all study sessions
      cursor.execute('DELETE FROM study_sessions')
      
      app.db.commit()
      
      return jsonify({"message": "Study history cleared successfully"}), 200
    except Exception as e:
      return jsonify({"error": str(e)}), 500