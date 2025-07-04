from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.glaria_quest import GlariaQuest
from app.schemas.glaria_quest_schema import GlariaQuestCreate, GlariaQuestOut
from typing import List

router = APIRouter(prefix="/api/glaria-quests", tags=["Glaria Quests"])


@router.post("/", response_model=GlariaQuestOut, status_code=201)
def create_glaria_quest(quest: GlariaQuestCreate, db: Session = Depends(get_db)):
    new_quest = GlariaQuest(**quest.dict())
    db.add(new_quest)
    db.commit()
    db.refresh(new_quest)
    return new_quest


@router.get("/", response_model=List[GlariaQuestOut])
def get_all_glaria_quests(db: Session = Depends(get_db)):
    return db.query(GlariaQuest).all()