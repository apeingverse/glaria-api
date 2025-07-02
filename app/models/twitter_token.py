from sqlalchemy import Column, Integer, String, Text, DateTime
from datetime import datetime
from app.database import Base


class TwitterToken(Base):
    __tablename__ = "twitter_tokens"

    id = Column(Integer, primary_key=True, index=True)
    twitter_id = Column(String, unique=True, index=True, nullable=False)
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)