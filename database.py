# app/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config import settings
from extensions import Base

engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
