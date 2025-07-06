from sqlalchemy import Column, Integer, ForeignKey, DateTime, UniqueConstraint, func
from app.database import Base

class UserCompletedQuest(Base):
    __tablename__ = "user_completed_quests"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    quest_id = Column(Integer, ForeignKey("quests.id", ondelete="CASCADE"))
    collected_at = Column(DateTime, server_default=func.now())
    __table_args__ = (UniqueConstraint("user_id", "quest_id", name="_user_quest_uc"),)