from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, ForeignKey
from app.database import Base
from sqlalchemy.orm import relationship

class Quest(Base):
    __tablename__ = "quests"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    points = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    actions = relationship("QuestAction", back_populates="quest", cascade="all, delete-orphan")


class QuestAction(Base):
    __tablename__ = "quest_actions"

    id = Column(Integer, primary_key=True, index=True)
    quest_id = Column(Integer, ForeignKey("quests.id", ondelete="CASCADE"), nullable=False)
    type = Column(String, nullable=False)         # e.g., "follow", "like"
    button_type = Column(String, nullable=False)  # e.g., "Follow", "Like"
    target_url = Column(String, nullable=True)

    quest = relationship("Quest", back_populates="actions")

