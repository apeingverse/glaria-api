from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class QuestCreate(BaseModel):
    project_id: int = Field(..., description="ID of the associated project")
    title: str = Field(..., description="Title of the quest")
    description: str = Field(..., description="Detailed description of the quest")
    type: str = Field(..., description="Type of quest, e.g., follow, like, visit")
    target_url: str = Field(..., description="Target URL for the quest")
    points: int = Field(0, description="XP reward for completing this quest")


class QuestOut(BaseModel):
    id: int
    project_id: int
    title: str
    description: str
    type: str
    target_url: str
    points: int
    created_at: datetime

    model_config = {"from_attributes": True}