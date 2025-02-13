from flask import request, jsonify, g
from flask_cors import cross_origin
import json
from services.group_service import GroupService

def load(app):
  @app.route('/api/groups', methods=['GET'])
  @cross_origin()
  def get_groups():
    try:
      page = int(request.args.get('page', 1))
      per_page = int(request.args.get('per_page', 10))
      sort_by = request.args.get('sort_by', 'name')
      order = request.args.get('order', 'asc')
      
      service = GroupService(app.db)
      result = service.get_groups(page, per_page, sort_by, order)
      
      return jsonify({
        'groups': result.items,
        'total_pages': result.total_pages,
        'current_page': result.current_page,
        'total_items': result.total_items
      })
    except ValueError as e:
      return jsonify({"error": "Invalid pagination parameters"}), 400
    except Exception as e:
      return jsonify({"error": str(e)}), 500

  @app.route('/groups/<int:id>', methods=['GET'])
  @cross_origin()
  def get_group(id):
    try:
      cursor = app.db.cursor()

      # Get group details
      cursor.execute('''
        SELECT id, name, words_count
        FROM groups
        WHERE id = ?
      ''', (id,))
      
      group = cursor.fetchone()
      if not group:
        return jsonify({"error": "Group not found"}), 404

      return jsonify({
        "id": group["id"],
        "group_name": group["name"],
        "word_count": group["words_count"]
      })
    except Exception as e:
      return jsonify({"error": str(e)}), 500

  @app.route('/api/groups/<int:id>/words', methods=['GET'])
  @cross_origin()
  def get_group_words(id):
    try:
      page = int(request.args.get('page', 1))
      per_page = int(request.args.get('per_page', 10))
      sort_by = request.args.get('sort_by', 'spanish')
      order = request.args.get('order', 'asc')
      
      service = GroupService(app.db)
      result = service.get_group_words(id, page, per_page, sort_by, order)
      
      if result is None:
        return jsonify({"error": "Group not found"}), 404
        
      return jsonify({
        'words': result.items,
        'total_pages': result.total_pages,
        'current_page': result.current_page,
        'total_items': result.total_items
      })
    except ValueError as e:
      return jsonify({"error": "Invalid pagination parameters"}), 400
    except Exception as e:
      return jsonify({"error": str(e)}), 500

  @app.route('/api/groups/<int:id>/words/raw', methods=['GET'])
  @cross_origin()
  def get_group_words_raw(id):
    """Get raw words for a group without study statistics.
    
    Args:
        id (int): The group ID
        
    Returns:
        tuple: (JSON response, HTTP status code)
    """
    try:
      service = GroupService(app.db)
      words = service.get_group_words_raw(id)
      
      if words is None:
        return jsonify({"error": "Group not found"}), 404
      
      return jsonify({
        'items': [{
          'id': word.id,
          'spanish': word.spanish,
          'english': word.english
        } for word in words]
      })

    except Exception as e:
      return jsonify({"error": str(e)}), 500

  @app.route('/groups/<int:id>/study_sessions', methods=['GET'])
  @cross_origin()
  def get_group_study_sessions(id):
    try:
      page = int(request.args.get('page', 1))
      per_page = 10
      sort_by = request.args.get('sort_by', 'created_at')
      order = request.args.get('order', 'desc')
      
      service = GroupService(app.db)
      result = service.get_group_study_sessions(id, page, per_page, sort_by, order)
      
      if result is None:
        return jsonify({"error": "Group not found"}), 404
        
      return jsonify({
        'sessions': result.items,
        'total_pages': result.total_pages,
        'current_page': result.current_page
      })
    except Exception as e:
      return jsonify({"error": str(e)}), 500