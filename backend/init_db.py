"""
Initialize database - Run this from backend folder
"""
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

from app.db.create_tables import create_tables
from app.db.seed import seed_all

if __name__ == "__main__":
    print("Creating tables...")
    create_tables()
    print("\nSeeding data...")
    seed_all()
    print("\n✅ Database initialization complete!")