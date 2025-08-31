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
