-- Create initial tables
CREATE TABLE IF NOT EXISTS groups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS words (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    spanish TEXT NOT NULL,
    english TEXT NOT NULL,
    UNIQUE(spanish, english)
);

CREATE TABLE IF NOT EXISTS word_groups (
    word_id INTEGER,
    group_id INTEGER,
    FOREIGN KEY (word_id) REFERENCES words(id),
    FOREIGN KEY (group_id) REFERENCES groups(id),
    UNIQUE(word_id, group_id)
);

CREATE TABLE IF NOT EXISTS study_activities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    launch_url TEXT NOT NULL,
    preview_url TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS study_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id INTEGER NOT NULL,
    study_activity_id INTEGER NOT NULL,
    created_at TIMESTAMP NOT NULL,
    FOREIGN KEY (group_id) REFERENCES groups (id),
    FOREIGN KEY (study_activity_id) REFERENCES study_activities (id)
);

CREATE TABLE IF NOT EXISTS word_review_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    study_session_id INTEGER NOT NULL,
    word_id INTEGER NOT NULL,
    correct BOOLEAN NOT NULL,
    created_at TIMESTAMP NOT NULL,
    FOREIGN KEY (study_session_id) REFERENCES study_sessions (id),
    FOREIGN KEY (word_id) REFERENCES words (id)
);

-- Insert initial study activities
INSERT OR REPLACE INTO study_activities (name, launch_url, preview_url) VALUES
    ('Flashcards', 'http://localhost:8080', '/assets/previews/flashcards.png'),
    ('Multiple Choice', 'http://localhost:8081', '/assets/previews/multiple-choice.png'),
    ('Spelling', 'http://localhost:8082', '/assets/previews/spelling.png'),
    ('Translation', 'http://localhost:8083', '/assets/previews/translation.png'),
    ('Writing Practice', 'http://localhost:8084', '/assets/previews/writing-practice.png'); 