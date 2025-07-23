from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class GlariaQuestCreate(BaseModel):
    title: str = Field(..., example="Follow GLARIA on X")
    description: str = Field(..., example="Follow us to earn XP")
    type: str = Field(..., example="follow")  # internal logic
    button_type: str = Field(..., example="Follow")  # frontend label
    target_url: Optional[str] = None
    points: int = Field(default=0)

class GlariaQuestOut(BaseModel):
    id: int
    title: str
    description: str
    type: str
    button_type: str
    target_url: Optional[str]
    points: int
    completed: Optional[bool] = None

    class Config:
        from_attributes = True