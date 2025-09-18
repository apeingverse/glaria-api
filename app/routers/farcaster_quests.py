from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.database import get_db
from app.models.farcaster import FarcasterQuest, FarcasterProject, FarcasterUser
from app.schemas.farcaster import FarcasterQuestOut, FarcasterQuestSchema
from pydantic import BaseModel
from app.auth.token import get_current_user

router = APIRouter(prefix="/farcaster", tags=["Farcaster Quests"])


# =======================
# Get all quests
# =======================
@router.get("/quests", response_model=List[FarcasterQuestOut])
def get_all_quests(db: Session = Depends(get_db)):
    return db.query(FarcasterQuest).all()


# =======================
# Get single quest by ID
# =======================
@router.get("/quests/{quest_id}", response_model=FarcasterQuestOut)
def get_quest_by_id(quest_id: int, db: Session = Depends(get_db)):
    quest = db.query(FarcasterQuest).get(quest_id)
    if not quest:
        raise HTTPException(status_code=404, detail="Quest not found")
    return quest


# =======================
# Get quests by project
# =======================
@router.get("/quests/project/{project_id}", response_model=List[FarcasterQuestOut])
def get_quests_by_project(project_id: int, db: Session = Depends(get_db)):
    return db.query(FarcasterQuest).filter(FarcasterQuest.project_id == project_id).all()


# =======================
# Create quest
# =======================
class CreateQuestIn(BaseModel):
    title: str
    description: str
    type: str
    button_type: str
    target_url: Optional[str] = None
    points: int
    project_id: int


@router.post("/quests", response_model=FarcasterQuestOut)
def create_quest(
    payload: CreateQuestIn,
    db: Session = Depends(get_db),
    user: FarcasterUser = Depends(get_current_user),
):
    project = db.query(FarcasterProject).get(payload.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    quest = FarcasterQuest(
        title=payload.title.strip(),
        description=payload.description.strip(),
        type=payload.type.strip(),
        button_type=payload.button_type.strip(),
        target_url=payload.target_url,
        points=payload.points,
        project_id=payload.project_id,
        created_at=datetime.utcnow(),
    )
    db.add(quest)
    db.commit()
    db.refresh(quest)
    return quest