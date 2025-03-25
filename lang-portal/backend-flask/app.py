from flask import Flask, g
from flask_cors import CORS

from lib.db import Db

import routes.words
import routes.groups
import routes.study_sessions
import routes.dashboard
import routes.study_activities

def create_app(test_config=None):
    app = Flask(__name__)
    
    # More explicit CORS configuration
    CORS(app, 
         origins=["http://localhost:5173"],  # Explicitly allow your React app
         supports_credentials=False,
         methods=["GET", "POST", "OPTIONS"])
    
    if test_config is None:
        app.config.from_mapping(
            DATABASE='words.db'
        )
    else:
        app.config.update(test_config)
    
    # Initialize database
    app.db = Db(database=app.config['DATABASE'])

    # Close database connection
    @app.teardown_appcontext
    def close_db(exception):
        app.db.close()

    # load routes -----------
    routes.words.load(app)
    routes.groups.load(app)
    routes.study_sessions.load(app)
    routes.dashboard.load(app)
    routes.study_activities.load(app)
    
    return app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True, port=5001)  # debug=True will show detailed errors