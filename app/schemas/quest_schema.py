from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


# ACTION SCHEMA
class QuestActionCreate(BaseModel):
    type: str
    button_type: str
    target_url: Optional[str]


class QuestActionOut(BaseModel):
    id: int
    type: str
    button_type: str
    target_url: Optional[str]

    class Config:
        orm_mode = True
    class Config:
        from_attributes = True


# QUEST CREATE + RESPONSE SCHEMA
class QuestCreate(BaseModel):
    project_id: int
    title: str
    description: str
    points: int
    project_points: int
    actions: List[QuestActionCreate]


class QuestOut(BaseModel):
    id: int
    project_id: int
    title: str
    description: str
    created_at: datetime
    actions: List[QuestActionOut]
    completed: bool = False  # 👈 Add this line


    class Config:
        orm_mode = True


# OPTIONAL: QUEST LISTING WITHOUT ACTIONS
class QuestSummary(BaseModel):
    id: int
    project_id: int
    title: str
    description: str
    points: int
    project_points: int

    class Config:
        orm_mode = True


class RandomQuestOut(BaseModel):
    id: int
    project_id: int
    title: str
    description: str

    model_config = {"from_attributes": True}