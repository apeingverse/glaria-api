# app/database.py

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:yourpassword@localhost/glaria_db")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

print("📦 Loaded DB URL =", DATABASE_URL)

# Dependency to use in routes
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()