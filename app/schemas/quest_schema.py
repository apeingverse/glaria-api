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


# QUEST CREATE + RESPONSE SCHEMA
class QuestCreate(BaseModel):
    project_id: int
    title: str
    description: str
    points: int
    actions: List[QuestActionCreate]


class QuestOut(BaseModel):
    id: int
    project_id: int
    title: str
    description: str
    points: int
    created_at: datetime
    actions: List[QuestActionOut]

    class Config:
        orm_mode = True


# OPTIONAL: QUEST LISTING WITHOUT ACTIONS
class QuestSummary(BaseModel):
    id: int
    project_id: int
    title: str
    description: str
    points: int

    class Config:
        orm_mode = True