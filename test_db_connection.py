from dotenv import load_dotenv
import os
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

load_dotenv()

def main():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("ERROR: DATABASE_URL is not set in environment or .env file")
        return

    print("Using DATABASE_URL:", db_url if len(db_url) < 120 else db_url[:120] + "...")

    try:
        # Short connect timeout to fail fast on network issues
        engine = create_engine(db_url, connect_args={"connect_timeout": 5})
        with engine.connect() as conn:
            r = conn.execute(text("SELECT version();"))
            version = r.scalar()
            print("Connected successfully. Server version:", version)
    except SQLAlchemyError as e:
        # SQLAlchemy wraps DBAPI errors; print repr for details
        print("SQLAlchemyError:", repr(e))
    except Exception as e:
        print("Unexpected error:", repr(e))

if __name__ == '__main__':
    main()
