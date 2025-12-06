#!/usr/bin/env python3
"""
Migration script to add status column to loans table
Run this once to update existing database schema
"""

from sqlalchemy import create_engine, text
from database import DATABASE_URL, logger
import os

def migrate_loan_status():
    """Add status column to loans table if it doesn't exist"""
    try:
        engine = create_engine(DATABASE_URL)
        
        with engine.connect() as conn:
            # Check if status column exists
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='loans' AND column_name='status'
            """))
            
            if result.fetchone() is None:
                logger.info("Adding status column to loans table...")
                conn.execute(text("""
                    ALTER TABLE loans 
                    ADD COLUMN status VARCHAR NOT NULL DEFAULT 'active'
                """))
                conn.commit()
                logger.info("Status column added successfully!")
            else:
                logger.info("Status column already exists in loans table")
                
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise

if __name__ == "__main__":
    migrate_loan_status()
    print("Migration completed!")