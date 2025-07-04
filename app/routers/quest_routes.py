# routers/quest_routes.py

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.auth.token import get_current_user
from app.database import get_db
from app.models.quests import Quest
from app.models.project import Project
from app.models.user import User
from app.schemas.quest_schema import QuestCreate, QuestOut, QuestSummary

router = APIRouter(prefix="/api/quests", tags=["Quests"])

@router.post("/", response_model=QuestOut)
def create_quest(
    quest: QuestCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    # Empty field check
    required_fields = ["title", "description", "type", "target_url"]
    empty_fields = [
        field for field in required_fields
        if not getattr(quest, field).strip() or getattr(quest, field).strip().lower() == "string"
    ]

    if empty_fields:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": f"You cannot leave these fields empty: {', '.join(empty_fields)}"}
        )

    new_quest = Quest(**quest.dict())
    db.add(new_quest)
    db.commit()
    db.refresh(new_quest)

    return new_quest


@router.get("/", response_model=List[QuestSummary])
def get_all_quests(db: Session = Depends(get_db)):
    quests = db.query(Quest).all()
    return quests


@router.get("/by-project/{project_id}", response_model=list[QuestOut])
def get_quests_by_project(project_id: int, db: Session = Depends(get_db)):
    quests = db.query(Quest).filter(Quest.project_id == project_id).all()

    if not quests:
        raise HTTPException(status_code=404, detail="No quests found for this project")

    return quests


@router.get("/{quest_id}", response_model=QuestOut)
def get_quest_by_id(quest_id: int, db: Session = Depends(get_db)):
    quest = db.query(Quest).filter_by(id=quest_id).first()
    if not quest:
        raise HTTPException(status_code=404, detail="Quest not found")
    return quest