# Plan to Implement the `/study_sessions` POST Endpoint

Below is a step-by-step plan to implement the `POST /study_sessions` endpoint in a Flask application. Each step is kept as simple and atomic as possible, with checkboxes for easy tracking and a short example testing snippet at the end.

---

## Overview

This endpoint should:
- Accept JSON data containing the `group_id` and `study_activity_id`.
- Validate that the required data is present.
- Insert a new record into the `study_sessions` table with the provided data.
- Return the newly created study session (e.g., its `id`, `group_id`, `study_activity_id`, `created_at`).

---

## Implementation Steps

1. [ ] **Create the Route**
   - In your `load(app)` function or an appropriate place in your code, add a new route for `POST /study_sessions`.

2. [ ] **Import Required Modules**
   - Make sure you have already imported:
     - `request` and `jsonify` from `flask`.
     - `datetime` from Python's standard library (if you need to set a timestamp).

3. [ ] **Extract and Validate Input**
   - Inside your new POST route:
     - Retrieve the JSON data with `request.get_json()`.
     - Check if both `group_id` and `study_activity_id` exist in the incoming data. If either is missing, return a 400 HTTP status code with an appropriate error message.

4. [ ] **Prepare Database Insertion**
   - Get a cursor from your database connection (e.g., `cursor = app.db.cursor()`).
   - Create the `INSERT` SQL statement with placeholders for the parameters.

5. [ ] **Handle the Timestamp (if needed)**
   - If you want the `created_at` field to always be "now," you can set it in the code before insertion.
     ```python
     created_at = datetime.now()
     ```

6. [ ] **Execute the Insert and Commit**
   - Execute the SQL statement with the user-provided `group_id` and `study_activity_id`, and optional `created_at`.
   - Commit the transaction to save the changes.

7. [ ] **Fetch the Newly Created Session**
   - After the insert, retrieve the last inserted `id` (depending on the database, you may do `cursor.lastrowid` or a specific function).
   - Perform a `SELECT` to fetch the inserted row and any related data (e.g., group name, study activity name).

8. [ ] **Build and Return the JSON Response**
   - Convert the fetched row into a JSON-serializable dictionary.
   - Return that dictionary with a 201 HTTP status code or a success message.

9. [ ] **Error Handling**
   - Wrap operations in a `try-except` block.
   - If an error occurs, return a JSON object with the error message and a 500 HTTP status code.

---

## Example Code Snippet

Below is a **rough** example illustrating how the new endpoint might look. Adapt it to match your project's coding style and variable naming.

```python
from flask import request, jsonify
from datetime import datetime

@app.route('/api/study_sessions', methods=['POST'])
@cross_origin()
def create_study_session():
    try:
        data = request.get_json()  # Get the JSON data from the request
        group_id = data.get('group_id')
        study_activity_id = data.get('study_activity_id')

        if group_id is None or study_activity_id is None:
            return jsonify({"error": "Missing required fields: group_id or study_activity_id"}), 400

        # Create a timestamp for the new session
        created_at = datetime.now()

        cursor = app.db.cursor()
        
        # Insert the new study session
        insert_stmt = '''
            INSERT INTO study_sessions (group_id, study_activity_id, created_at)
            VALUES (?, ?, ?)
        '''
        cursor.execute(insert_stmt, (group_id, study_activity_id, created_at))
        
        # Get the newly created session ID
        new_session_id = cursor.lastrowid
        
        # Commit the changes
        app.db.commit()
        
        # Optionally, fetch the newly created session
        cursor.execute('''
            SELECT 
                ss.id,
                ss.group_id,
                g.name as group_name,
                sa.id as activity_id,
                sa.name as activity_name,
                ss.created_at
            FROM study_sessions ss
            JOIN groups g ON g.id = ss.group_id
            JOIN study_activities sa ON sa.id = ss.study_activity_id
            WHERE ss.id = ?
        ''', (new_session_id,))
        
        new_session = cursor.fetchone()
        
        # Build the response
        response = {
            "id": new_session["id"],
            "group_id": new_session["group_id"],
            "group_name": new_session["group_name"],
            "activity_id": new_session["activity_id"],
            "activity_name": new_session["activity_name"],
            "start_time": new_session["created_at"].isoformat(),
            "end_time": new_session["created_at"].isoformat()  # if you are using the same value for now
        }
        
        return jsonify(response), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500
