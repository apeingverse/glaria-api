from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field

from enum import Enum


class ProjectTypeEnum(str, Enum):
    NFT = "NFT"
    GameFi = "GameFi"
    DeFi = "DeFi"



class ProjectCreate(BaseModel):
    name: str = Field(..., description="Project name")
    twitter_username: str = Field(..., description="Twitter username")
    description: str = Field(..., description="Project description")
    image_url: Optional[str] = Field(None, description="URL of the project image")
    project_type: ProjectTypeEnum
    discord_url: Optional[str] = None
    telegram_url: Optional[str] = None
    twitter_url: Optional[str] = None


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    twitter_username: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None

    discord_url: Optional[str] = None
    telegram_url: Optional[str] = None
    twitter_url: Optional[str] = None



class ProjectOut(ProjectCreate):
    id: int
    name: str
    twitter_username: str
    description: Optional[str]
    image_url: Optional[str] = None
    project_type: ProjectTypeEnum
    discord_url: Optional[str] = None
    telegram_url: Optional[str] = None
    twitter_url: Optional[str] = None
    created_at: datetime

    model_config = {
        "from_attributes": True,
        "arbitrary_types_allowed": True  # <-- ADD THIS
    }


class ProjectListItem(BaseModel):
    id: int
    name: str
    twitter_username: str
    description: Optional[str]
    image_url: Optional[str] = None
    project_type: ProjectTypeEnum



    model_config = {"from_attributes": True}