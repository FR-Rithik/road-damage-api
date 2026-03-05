from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings

engine = create_engine(settings.database_url)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# It imports settings from config.py to get the database URL.
# engine creates a connection to the database.
# SessionLocal is a factory for database sessions (used to interact with the DB).
# get_db() is a function that provides a database session for each request and ensures 
# it’s closed after use (using Python’s yield and
#  finally).