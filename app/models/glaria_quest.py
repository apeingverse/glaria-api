from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime
from app.database import Base

class GlariaQuest(Base):
    __tablename__ = "glaria_quests"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)                 # e.g. "Follow GLARIA on X"
    description = Column(Text, nullable=False)             # e.g. "Follow us to earn XP"
    type = Column(String, nullable=False)                  # internal type: follow, like, join_discord, etc.
    button_type = Column(String, nullable=False)           # frontend action label: "Follow", "Like", etc.
    target_url = Column(String, nullable=True)             # Optional: external URL
    points = Column(Integer, default=0)                    # XP reward
    created_at = Column(DateTime, default=datetime.utcnow)