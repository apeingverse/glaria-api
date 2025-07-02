from sqlalchemy import Column, Integer, String, Text, DateTime, func
from app.database import Base

class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    twitter_username = Column(String, unique=True, nullable=False)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    discord_url = Column(String, nullable=True)
    telegram_url = Column(String, nullable=True)
    twitter_url = Column(String, nullable=True)