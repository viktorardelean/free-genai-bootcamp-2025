from flask import request, jsonify, g
from flask_cors import cross_origin
from datetime import datetime
import math
from contextlib import contextmanager
from services.study_session_service import StudySessionService

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
  @app.route('/api/study_sessions', methods=['POST'])
  @cross_origin()
  def create_study_session():
    """Create a new study session.
    
    Accepts JSON payload with group_id and study_activity_id.
    Validates inputs, creates session, and returns the created session data.
    
    Returns:
        tuple: (JSON response, HTTP status code)
    """
    try:
        data = request.get_json()
        if not data or 'group_id' not in data or 'study_activity_id' not in data:
            return jsonify({
                "error": "Missing required fields: group_id, study_activity_id"
            }), 400
            
        if not isinstance(data['group_id'], int) or not isinstance(data['study_activity_id'], int):
            return jsonify({
                "error": "group_id and study_activity_id must be integers"
            }), 400
        
        service = StudySessionService(app.db)
        session = service.create_session(data['group_id'], data['study_activity_id'])
        
        if session is None:
            return jsonify({
                "error": "Group or study activity not found"
            }), 404
        
        return jsonify({
            'id': session.id,
            'group_id': session.group_id,
            'study_activity_id': session.study_activity_id,
            'created_at': session.created_at,
            'group_name': session.group_name,
            'activity_name': session.activity_name
        }), 201

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

  @app.route('/api/study_sessions/<int:session_id>/words/<int:word_id>/review', methods=['POST'])
  @cross_origin()
  def review_word(session_id, word_id):
    try:
        data = request.get_json()
        if 'correct' not in data:
            return jsonify({
                "error": "Missing required field: correct"
            }), 400
        
        service = StudySessionService(app.db)
        result = service.review_word(session_id, word_id, data['correct'])
        
        if result is None:
            return jsonify({
                "error": "Study session or word not found"
            }), 404
        
        return jsonify(result), 200
        
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