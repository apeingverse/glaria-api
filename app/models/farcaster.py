from sqlalchemy import Column, Integer, String, DateTime, Boolean, func
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class FarcasterNonce(Base):
    __tablename__ = "farcaster_nonces"

    id = Column(Integer, primary_key=True, index=True)
    nonce = Column(String(255), unique=True, nullable=False, index=True)  # random unique string
    fid = Column(Integer, nullable=True)  # set after successful login
    used = Column(Boolean, default=False)  # has this nonce been consumed?
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)  # when nonce becomes invalid
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