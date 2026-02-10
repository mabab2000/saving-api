#!/usr/bin/env python3
"""
Migration script to remove the legacy `photo` column from `profile_photos` table.
It reads `DATABASE_URL` from environment (.env) so you can run it from the project root.

Run:
    python scripts/remove_profilephotos_photo_column.py
"""
import os
import logging
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    logger.error("DATABASE_URL not found in environment. Ensure .env contains DATABASE_URL and retry.")
    raise SystemExit(1)


def remove_photo_column():
    try:
        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            # Check if column exists
            result = conn.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='profile_photos' AND column_name='photo'
            """))

            if result.fetchone() is not None:
                logger.info("Dropping column 'photo' from profile_photos...")
                conn.execute(text("ALTER TABLE profile_photos DROP COLUMN IF EXISTS photo;"))
                conn.commit()
                logger.info("Column 'photo' dropped successfully.")
            else:
                logger.info("Column 'photo' does not exist on profile_photos; nothing to do.")

    except Exception as e:
        logger.error(f"Failed to drop column 'photo': {e}")
        raise


if __name__ == '__main__':
    remove_photo_column()
