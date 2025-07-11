from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.glaria_quest import GlariaQuest
from app.schemas.glaria_quest_schema import GlariaQuestCreate, GlariaQuestOut
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth.token import get_current_user
from app.models.user import User
from app.models.glaria_quest import GlariaQuest
from app.models.user_completed_quest import UserCompletedQuest, QuestTypeEnum

from app.auth.token import get_current_user

router = APIRouter(prefix="/api/glaria-quests", tags=["Glaria Quests"])


@router.post("/", response_model=GlariaQuestOut, status_code=201)
def create_glaria_quest(quest: GlariaQuestCreate, db: Session = Depends(get_db)):
    new_quest = GlariaQuest(**quest.dict())
    db.add(new_quest)
    db.commit()
    db.refresh(new_quest)
    return new_quest


@router.get("/", response_model=List[GlariaQuestOut])
def get_glaria_quests(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)  # optional if you want unauth access
):
    quests = db.query(GlariaQuest).all()
    result = []

    for quest in quests:
        is_completed = db.query(UserCompletedQuest).filter_by(
            user_id=user.id, quest_id=quest.id, quest_type=QuestTypeEnum.glaria
        ).first() is not None

        result.append(GlariaQuestOut(
        id=quest.id,
        title=quest.title,
        description=quest.description,
        type=quest.type,
        button_type=quest.button_type,
        target_url=quest.target_url,
        points=quest.points,
        completed=is_completed
        ))

    return result



@router.post("/collect-glaria-xp")
def collect_glaria_xp(quest_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    # 1. Check if glaria quest exists
    quest = db.query(GlariaQuest).filter(GlariaQuest.id == quest_id).first()
    if not quest:
        raise HTTPException(status_code=404, detail="Glaria quest not found")

    # 2. Check if XP was already collected
    already_collected = db.query(UserCompletedQuest).filter_by(
        user_id=user.id, quest_id=quest_id, quest_type="glaria"
    ).first()
    if already_collected:
        raise HTTPException(status_code=400, detail="XP already collected for this glaria quest")

    # 3. Add XP to user
    user.xp += quest.points

    # 4. Record as completed
    db.add(UserCompletedQuest(user_id=user.id, quest_id=quest.id, quest_type="glaria"))
    db.commit()
    db.refresh(user)

    return {
        "message": "XP successfully collected from Glaria quest",
        "total_xp": user.xp
    }