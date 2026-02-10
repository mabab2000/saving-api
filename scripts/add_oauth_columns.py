"""
Migration script to add OAuth-related columns to the User table
Run this script to update your existing database with the new columns
"""
from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def add_oauth_columns():
    """Add OAuth columns to the saving_users table"""
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        try:
            # Make hashed_password nullable
            print("Making hashed_password column nullable...")
            conn.execute(text("""
                ALTER TABLE saving_users 
                ALTER COLUMN hashed_password DROP NOT NULL
            """))
            
            # Add oauth_provider column
            print("Adding oauth_provider column...")
            conn.execute(text("""
                ALTER TABLE saving_users 
                ADD COLUMN IF NOT EXISTS oauth_provider VARCHAR(50)
            """))
            
            # Add oauth_id column
            print("Adding oauth_id column...")
            conn.execute(text("""
                ALTER TABLE saving_users 
                ADD COLUMN IF NOT EXISTS oauth_id VARCHAR(255)
            """))
            
            # Add profile_picture column
            print("Adding profile_picture column...")
            conn.execute(text("""
                ALTER TABLE saving_users 
                ADD COLUMN IF NOT EXISTS profile_picture VARCHAR(500)
            """))
            
            conn.commit()
            print("✓ Migration completed successfully!")
            
        except Exception as e:
            conn.rollback()
            print(f"✗ Error during migration: {str(e)}")
            raise

if __name__ == "__main__":
    print("Starting OAuth columns migration...\n")
    add_oauth_columns()
