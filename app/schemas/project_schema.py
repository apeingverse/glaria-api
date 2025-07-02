from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field



class ProjectCreate(BaseModel):
    name: str = Field(..., description="Project name")
    twitter_username: str = Field(..., description="Twitter username")
    description: str = Field(..., description="Project description")
    discord_url: Optional[str] = None
    telegram_url: Optional[str] = None
    twitter_url: Optional[str] = None


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    twitter_username: Optional[str] = None
    description: Optional[str] = None
    discord_url: Optional[str] = None
    telegram_url: Optional[str] = None
    twitter_url: Optional[str] = None



class ProjectOut(BaseModel):
    id: int
    name: str
    twitter_username: str
    description: Optional[str]
    discord_url: Optional[str] = None
    telegram_url: Optional[str] = None
    twitter_url: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}