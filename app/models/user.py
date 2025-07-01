# models/user.py
from sqlalchemy import Column, Integer, String, UniqueConstraint
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)  # required & unique
    email = Column(String, nullable=True)
    twitter_id = Column(String, unique=True, nullable=True)             # from X
    twitter_username = Column(String, nullable=True)                    # from X
    wallet_address = Column(String, unique=True, nullable=True)         # if user connects wallet
    xp = Column(Integer, default=100)