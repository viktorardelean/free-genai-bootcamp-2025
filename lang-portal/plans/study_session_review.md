# Plan to Implement the `/study_sessions/:id/words/:word_id/review` POST Endpoint

Below is a step-by-step plan to implement the `POST /study_sessions/:id/words/:word_id/review` endpoint in a Flask application. Each step is kept as simple and atomic as possible, with checkboxes for easy tracking and a short example testing snippet at the end.

---

## Overview

This endpoint should:
- Accept JSON data containing the field `correct` (boolean).
- Validate that the field is present and is a boolean.
- Check that both the `study_session` and the `word` exist in the database.
- Insert a new record into the `word_review_items` table, linking the `study_session_id` and `word_id` with the `correct` value.
- Return a JSON response with details of the newly created review record (e.g., `study_session_id`, `word_id`, `correct`, `created_at`).

---

## Implementation Steps

1. [ ] **Create the Route**
   - In your `load(app)` function (or the file where you define routes), add a new route for `POST /study_sessions/:id/words/:word_id/review`.


2. [ ] **Import Required Modules**  
   - Make sure you have the following imports at the top of your file:
     ```python
     from flask import request, jsonify
     from datetime import datetime
     ```
   - If you're using **Flask-CORS**, ensure you've imported and applied `cross_origin`.
   - Confirm that you have access to the database connection via `app.db`.

3. [ ] **Extract and Validate Input**  
   - Inside your `review_word_in_session` route (from Step 1 in the full plan):
     - Retrieve the JSON data with `request.get_json()`.
     - Check if the `correct` field is present in the JSON data.
     - Verify that `correct` is a boolean. If it is missing or not a boolean, return a 400 HTTP status code with an error message.


4. [ ] **Check the Existence of Session and Word**  
   - Use the incoming `session_id` to verify that the `study_sessions` table contains a record with that ID.
   - Use the incoming `word_id` to verify that the `words` table has the corresponding word.
   - If either is missing, return a 404 HTTP status code with an appropriate message.

---

