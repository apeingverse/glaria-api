from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


# === Nonce Response ===
class FarcasterNonceResponse(BaseModel):
    nonce: str
    expires_at: datetime


# === Project Schemas ===
class FarcasterProjectSchema(BaseModel):
    id: int
    name: str
    description: Optional[str]
    image_url: Optional[str]
    created_at: Optional[str]  # You can switch to datetime if needed

    class Config:
        orm_mode = True


class ProjectListItem(BaseModel):
    id: int
    name: str
    image_url: Optional[str]

    class Config:
        orm_mode = True


class ProjectOut(BaseModel):
    id: int
    name: str
    description: Optional[str]
    image_url: Optional[str]
    created_at: Optional[datetime]

    class Config:
        orm_mode = True


# === Quest Schemas ===
class FarcasterQuestSchema(BaseModel):
    id: int
    project_id: int
    title: str
    description: Optional[str]
    type: str  # e.g., 'join_discord', 'follow', 'quote_cast'
    button_type: str  # frontend label, like 'Join', 'Follow'
    target_url: Optional[str]
    points: int
    created_at: Optional[datetime]

    class Config:
        orm_mode = True


class FarcasterQuestOut(BaseModel):
    id: int
    title: str
    description: str
    type: str
    button_type: str
    target_url: Optional[str]
    points: int
    project_id: int
    created_at: datetime

    class Config:
        orm_mode = True