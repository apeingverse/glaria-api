from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class Quest(Base):
    __tablename__ = "quests"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    type = Column(String, nullable=False)  # e.g., "like", "retweet", "follow", "discord", "website"
    title = Column(String, nullable=False)  # e.g., "Follow us on Twitter!"
    description = Column(Text, nullable=True)
    target_url = Column(String, nullable=False)  # The URL user needs to act on
    xp_reward = Column(Integer, default=50)
    xp = Column(Integer, default=0)  # Admin-assigned XP weight, for example

    project = relationship("Project", back_populates="quests")