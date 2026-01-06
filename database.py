from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base
import os
from dotenv import load_dotenv
import logging
from urllib.parse import quote_plus

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Support building DATABASE_URL from components (useful for SSH tunnel/local testing)
# Priority: if full DATABASE_URL is set, use it. Otherwise build from DB_HOST/DB_PORT/DB_USER/DB_PASSWORD/DB_NAME.
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    db_user = os.getenv("DB_USER")
    db_pass = os.getenv("DB_PASSWORD")
    db_host = os.getenv("DB_HOST")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME")

    if not (db_user and db_pass and db_host and db_name):
        logger.error("DATABASE_URL or DB_USER/DB_PASSWORD/DB_HOST/DB_NAME env vars must be set!")
        raise ValueError("Database configuration missing in environment")

    # URL-encode password in case it has special characters
    safe_pass = quote_plus(db_pass)
    DATABASE_URL = f"postgresql://{db_user}:{safe_pass}@{db_host}:{db_port}/{db_name}"

logger.info(f"Connecting to database: {DATABASE_URL[:40]}...")

try:
    # AWS RDS connection settings with extended timeout and SSL
    connect_args = {
        "connect_timeout": 30,
        "keepalives_idle": 600,
        "keepalives_interval": 30,
        "keepalives_count": 3,
    }
    
    # For Supabase pooled connections, add search_path to the URL options
    # This ensures the schema is set before any queries
    if "?" in DATABASE_URL:
        db_url = DATABASE_URL + "&options=-c%20search_path%3Dpublic"
    else:
        db_url = DATABASE_URL + "?options=-c%20search_path%3Dpublic"
    
    from sqlalchemy import event
    
    engine = create_engine(
        db_url, 
        connect_args=connect_args,
        pool_timeout=20,
        pool_recycle=3600,
        pool_pre_ping=True
    )
    
    # Set search_path on every new connection (works with connection poolers)
    @event.listens_for(engine, "connect")
    def set_search_path(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("SET search_path TO public")
        cursor.close()
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Create tables
    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully!")

except Exception as e:
    logger.error(f"Database connection failed: {str(e)}")
    raise

# Database Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()