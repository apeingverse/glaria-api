from sqlalchemy import Column, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database import Base

class UserProjectXP(Base):
    __tablename__ = "user_project_xp"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"))
    xp = Column(Integer, default=0)

    __table_args__ = (UniqueConstraint("user_id", "project_id", name="user_project_unique"),)