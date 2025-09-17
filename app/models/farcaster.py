from sqlalchemy import Column, ForeignKey, Integer, String, DateTime, Boolean, Text, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

# === Farcaster Identity ===

class FarcasterNonce(Base):
    __tablename__ = "farcaster_nonces"

    id = Column(Integer, primary_key=True, index=True)
    nonce = Column(String(255), unique=True, nullable=False, index=True)
    fid = Column(Integer, nullable=True)
    used = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)


class FarcasterUser(Base):
    __tablename__ = "farcaster_users"

    id = Column(Integer, primary_key=True, index=True)
    fid = Column(Integer, unique=True, nullable=False, index=True)
    custody_address = Column(String(255), nullable=False)
    username = Column(String(255))
    display_name = Column(String(255))
    pfp_url = Column(String(512))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # No ownership of projects anymore
    completed_quests = relationship("FarcasterUserCompletedQuest", back_populates="user", cascade="all, delete-orphan")

# === Projects ===

class FarcasterProject(Base):
    __tablename__ = "farcaster_projects"

    id = Column(Integer, primary_key=True, index=True)

    # Removed farcaster_user_id and creator relationship
    fid = Column(Integer, nullable=True)
    farcaster_username = Column(String(255), nullable=True)

    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    image_url = Column(String(512), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    quests = relationship("FarcasterQuest", back_populates="project", cascade="all, delete-orphan")

# === Quests ===

class FarcasterQuest(Base):
    __tablename__ = "farcaster_quests"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    type = Column(String(100), nullable=False)
    button_type = Column(String(100), nullable=False)
    target_url = Column(String(512), nullable=True)
    points = Column(Integer, default=10)

    project_id = Column(Integer, ForeignKey("farcaster_projects.id"), nullable=True)
    project = relationship("FarcasterProject", back_populates="quests")

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    actions = relationship("FarcasterQuestAction", back_populates="quest", cascade="all, delete-orphan")
    completions = relationship("FarcasterUserCompletedQuest", back_populates="quest", cascade="all, delete-orphan")


class FarcasterQuestAction(Base):
    __tablename__ = "farcaster_quest_actions"

    id = Column(Integer, primary_key=True, index=True)
    quest_id = Column(Integer, ForeignKey("farcaster_quests.id"), nullable=False)
    type = Column(String(100), nullable=False)
    target_url = Column(String(512), nullable=True)

    quest = relationship("FarcasterQuest", back_populates="actions")


class FarcasterUserCompletedQuest(Base):
    __tablename__ = "farcaster_user_completed_quests"

    id = Column(Integer, primary_key=True, index=True)

    farcaster_user_id = Column(Integer, ForeignKey("farcaster_users.id"), nullable=False)
    quest_id = Column(Integer, ForeignKey("farcaster_quests.id"), nullable=False)
    quest_type = Column(String(50), nullable=False)
    completed_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("FarcasterUser", back_populates="completed_quests")
    quest = relationship("FarcasterQuest", back_populates="completions")