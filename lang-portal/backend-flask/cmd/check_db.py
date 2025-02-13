import click
import sqlite3
from pathlib import Path

@click.command()
def check_db():
    """Check database status and contents"""
    db_path = Path(__file__).parent.parent / 'words.db'
    if not db_path.exists():
        click.echo("Database file not found!")
        return
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Check tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row['name'] for row in cursor.fetchall()]
    click.echo(f"\nTables found: {', '.join(tables)}")
    
    # Check groups and word counts
    cursor.execute("""
        SELECT g.name, COUNT(w.id) as word_count
        FROM groups g
        LEFT JOIN word_groups wg ON wg.group_id = g.id
        LEFT JOIN words w ON w.id = wg.word_id
        GROUP BY g.name
    """)
    click.echo("\nWord counts by group:")
    for row in cursor.fetchall():
        click.echo(f"  {row['name']}: {row['word_count']} words")
    
    # Check study activities
    cursor.execute("SELECT name FROM study_activities")
    activities = [row['name'] for row in cursor.fetchall()]
    click.echo(f"\nStudy activities: {', '.join(activities)}")

if __name__ == '__main__':
    check_db() 