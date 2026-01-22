import os
import sys
import logging
from dotenv import load_dotenv
import psycopg2

load_dotenv()

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    logger.error("DATABASE_URL not found in environment. Set DATABASE_URL in .env before running this script.")
    sys.exit(1)


def ensure_columns():
    sqls = [
        "ALTER TABLE profile_photos ADD COLUMN IF NOT EXISTS photo_url TEXT;",
        "ALTER TABLE profile_photos ADD COLUMN IF NOT EXISTS content_type TEXT;",
    ]

    conn = None
    try:
        logger.info("Connecting to database to ensure profile_photos columns...")
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = True
        cur = conn.cursor()

        for s in sqls:
            logger.info(f"Executing: {s}")
            cur.execute(s)

        logger.info("profile_photos columns ensured successfully.")
        cur.close()

    except Exception as e:
        logger.error(f"Error ensuring columns: {e}")
        raise
    finally:
        if conn:
            conn.close()


if __name__ == '__main__':
    ensure_columns()
