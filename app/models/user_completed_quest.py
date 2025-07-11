import enum
from sqlalchemy import Column, Enum, Integer, ForeignKey, DateTime, String, UniqueConstraint, func
from app.database import Base

class QuestTypeEnum(str, enum.Enum):
    glaria = "glaria"
    project = "project"

class UserCompletedQuest(Base):
    __tablename__ = "user_completed_quests"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    quest_id = Column(Integer, nullable=False)
    quest_type = Column(Enum(QuestTypeEnum), nullable=False)
    collected_at = Column(DateTime, server_default=func.now())
    __table_args__ = (UniqueConstraint("user_id", "quest_id", "quest_type", name="_user_quest_uc"),)