from sqlalchemy import Column, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class WalletNonce(Base):
    __tablename__ = "wallet_nonces"
    address = Column(String, primary_key=True)
    nonce = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)