from flask import jsonify, request, current_app
from flask_cors import cross_origin
import math
from services.study_activity_service import StudyActivityService
import traceback

def load(app):
    service = StudyActivityService(app.db)

    @app.route('/api/study-activities', methods=['GET'])
    @cross_origin()
    def get_study_activities():
        """Get all study activities."""
        try:
            activities = service.get_all_activities()
            return jsonify(activities)
        except Exception as e:
            app.logger.error(f'Error in get_study_activities: {str(e)}')
            app.logger.error(traceback.format_exc())
            return jsonify({"error": str(e)}), 500

    @app.route('/api/study-activities/<int:id>', methods=['GET'])
    @cross_origin()
    def get_study_activity(id):
        """Get a single study activity by ID."""
        try:
            activity = service.get_activity(id)
            
            if activity is None:
                return jsonify({"error": "Activity not found"}), 404
            else:
                return jsonify(activity)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route('/api/study-activities', methods=['POST'])
    @cross_origin()
    def create_study_activity():
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'launch_url', 'preview_url']
        if not all(field in data for field in required_fields):
            return jsonify({'error': 'Missing required fields'}), 400
            
        try:
            activity = service.create_activity(
                name=data['name'],
                launch_url=data['launch_url'],
                preview_url=data['preview_url']
            )
            return jsonify(activity), 201
        except Exception as e:
            current_app.logger.error(f"Error creating activity: {str(e)}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/study-activities/<int:id>/sessions', methods=['GET'])
    @cross_origin()
    def get_study_activity_sessions(id):
        cursor = app.db.cursor()
        
        # Verify activity exists
        cursor.execute('SELECT id FROM study_activities WHERE id = ?', (id,))
        if not cursor.fetchone():
            return jsonify({'error': 'Activity not found'}), 404

        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        offset = (page - 1) * per_page

        # Get total count
        cursor.execute('''
            SELECT COUNT(*) as count 
            FROM study_sessions ss
            JOIN groups g ON g.id = ss.group_id
            WHERE ss.study_activity_id = ?
        ''', (id,))
        total_count = cursor.fetchone()['count']

        # Get paginated sessions
        cursor.execute('''
            SELECT 
                ss.id,
                ss.group_id,
                g.name as group_name,
                sa.name as activity_name,
                ss.created_at,
                ss.study_activity_id as activity_id,
                COUNT(wri.id) as review_items_count
            FROM study_sessions ss
            JOIN groups g ON g.id = ss.group_id
            JOIN study_activities sa ON sa.id = ss.study_activity_id
            LEFT JOIN word_review_items wri ON wri.study_session_id = ss.id
            WHERE ss.study_activity_id = ?
            GROUP BY ss.id, ss.group_id, g.name, sa.name, ss.created_at, ss.study_activity_id
            ORDER BY ss.created_at DESC
            LIMIT ? OFFSET ?
        ''', (id, per_page, offset))
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

    @app.route('/api/study-activities/<int:activity_id>/launch', methods=['GET'])
    @cross_origin()
    def get_study_activity_launch_data(activity_id):
        try:
            cursor = app.db.cursor()
            
            # First get the activity details
            cursor.execute('''
                SELECT id, name, launch_url, preview_url
                FROM study_activities 
                WHERE id = ?
            ''', (activity_id,))
            
            activity = cursor.fetchone()
            if not activity:
                return jsonify({"error": "Activity not found"}), 404
            
            # Get all available groups
            cursor.execute('''
                SELECT g.id, g.name, COUNT(wg.word_id) as word_count
                FROM groups g
                LEFT JOIN word_groups wg ON g.id = wg.group_id
                GROUP BY g.id, g.name
                ORDER BY g.name
            ''')
            
            groups = cursor.fetchall()
            
            return jsonify({
                'activity': {
                    'id': activity['id'],
                    'title': activity['name'],
                    'type': 'writing',  # Hardcode type since it's not in DB
                    'launch_url': activity['launch_url'],
                    'preview_url': activity['preview_url']
                },
                'groups': [{
                    'id': group['id'],
                    'name': group['name'],
                    'word_count': group['word_count']
                } for group in groups]
            })
            
        except Exception as e:
            app.logger.error(f"Error getting launch data: {str(e)}")
            app.logger.error(traceback.format_exc())
            return jsonify({"error": str(e)}), 500
