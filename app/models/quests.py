from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, ForeignKey
from app.database import Base

class Quest(Base):
    __tablename__ = "quests"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    type = Column(String, nullable=False)  # Defi, NFT, GameFi
    target_url = Column(String, nullable=False)
    points = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

