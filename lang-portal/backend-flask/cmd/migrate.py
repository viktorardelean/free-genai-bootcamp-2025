import click
from db.init_db import init_db, main as seed_db

@click.group()
def cli():
    """Database management commands"""
    pass

@cli.command()
def migrate():
    """Run database migrations"""
    init_db()

@cli.command()
def seed():
    """Seed database with initial data"""
    seed_db()

if __name__ == '__main__':
    cli() 