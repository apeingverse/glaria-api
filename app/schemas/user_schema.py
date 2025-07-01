# schemas/user_schema.py
from pydantic import BaseModel
from typing import Optional

class UserCreate(BaseModel):
    username: str
    email: Optional[str] = None
    twitter_id: Optional[str] = None
    twitter_username: Optional[str] = None
    wallet_address: Optional[str] = None


class UserResponse(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    twitter_id: Optional[str] = None
    twitter_username: Optional[str] = None
    wallet_address: Optional[str] = None
    xp: int

    class Config:
        orm_mode = True