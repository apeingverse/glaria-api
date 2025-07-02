from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum

class QuestType(str, Enum):
    defi = "DeFi"
    nft = "NFT"
    gamefi = "GameFi"



class QuestCreate(BaseModel):
    project_id: int
    title: str
    description: str
    type: QuestType
    target_url: str
    points: int


class QuestOut(BaseModel):
    id: int
    project_id: int
    title: str
    description: str
    type: QuestType
    target_url: str
    points: int
    created_at: datetime

    model_config = {"from_attributes": True}


class QuestSummary(BaseModel):
    id: int
    project_id: int
    title: str
    description: str
    type: QuestType
    points: int

    model_config = {"from_attributes": True}

