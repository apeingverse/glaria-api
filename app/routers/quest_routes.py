# routers/quest_routes.py

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
from jose import JWTError
from jose import jwt
from sqlalchemy.orm import Session

from app.auth.token import ALGORITHM, SECRET_KEY, get_current_user
from app.database import get_db
from app.models.quests import Quest, QuestAction
from app.models.project import Project
from app.models.user import User
from app.models.user_completed_quest import UserCompletedQuest
from app.models.user_project_xp import UserProjectXP
from app.schemas.quest_schema import QuestActionOut, QuestCreate, QuestOut, QuestSummary



security = HTTPBearer(auto_error=False)
router = APIRouter(prefix="/api/quests", tags=["Quests"])

@router.post("/", response_model=QuestOut)
def create_quest(quest: QuestCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    # Manual empty check
    required_fields = ["title", "description"]
    empty_fields = [field for field in required_fields if not getattr(quest, field).strip() or getattr(quest, field).strip().lower() == "string"]
    if empty_fields:
        raise HTTPException(status_code=400, detail=f"You cannot leave these fields empty: {', '.join(empty_fields)}")

    # Create main Quest
    new_quest = Quest(
        project_id=quest.project_id,
        title=quest.title,
        description=quest.description,
        points=quest.points,
        project_points=quest.project_points
    )

    # Convert action dicts to QuestAction model instances
    new_quest.actions = [
        QuestAction(
            type=action.type,
            button_type=action.button_type,
            target_url=action.target_url
        ) for action in quest.actions
    ]

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


@router.get("/completed")
def get_total_completed_quests(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    total = db.query(UserCompletedQuest).filter_by(user_id=user.id).count()
    return {"total_claimed_quests": total}


@router.get("/{quest_id}", response_model=QuestOut)
def get_quest_by_id(
    quest_id: int,
    db: Session = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security)
):
    # 1. Get quest
    quest = db.query(Quest).filter(Quest.id == quest_id).first()
    if not quest:
        raise HTTPException(status_code=404, detail="Quest not found")

    # 2. Convert actions to schema
    actions_out = [QuestActionOut.from_orm(action) for action in quest.actions]

    # 3. Default
    completed = False

    # 4. Optional user check
    if credentials:
        try:
            payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
            user_id = int(payload.get("sub"))
            completed = db.query(UserCompletedQuest).filter_by(user_id=user_id, quest_id=quest.id).first() is not None
        except JWTError:
            pass  # Invalid token, ignore

    # 5. Return response (no points info)
    return QuestOut(
        id=quest.id,
        project_id=quest.project_id,
        title=quest.title,
        description=quest.description,
        created_at=quest.created_at,
        actions=actions_out,
        completed=completed
    )



@router.get("/xp-by-quest/{quest_id}")
def xp_by_quest_id(quest_id: int, db: Session = Depends(get_db)):
    quest = db.query(Quest).filter(Quest.id == quest_id).first()
    if not quest:
        raise HTTPException(status_code=404, detail="Quest not found")

    return {
        "quest_id": quest.id,
        "points": quest.points,
        "project_points": quest.project_points
    }



@router.post("/collect-xp")
def collect_xp(quest_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    # 1. Check if quest exists
    quest = db.query(Quest).filter(Quest.id == quest_id).first()
    if not quest:
        raise HTTPException(status_code=404, detail="Quest not found")

    # 2. Prevent duplicate collection
    already_collected = db.query(UserCompletedQuest).filter_by(user_id=user.id, quest_id=quest_id).first()
    if already_collected:
        raise HTTPException(status_code=400, detail="XP already collected for this quest")

    # 3. Add Glaria XP to user's xp column
    user.xp += quest.points

    # 4. Add Project XP to user_project_xp
    project_xp = (
        db.query(UserProjectXP)
        .filter_by(user_id=user.id, project_id=quest.project_id)
        .first()
    )

    if project_xp:
        project_xp.xp += quest.project_points
    else:
        project_xp = UserProjectXP(
            user_id=user.id,
            project_id=quest.project_id,
            xp=quest.project_points
        )
        db.add(project_xp)

    # 5. Mark quest as completed
    db.add(UserCompletedQuest(user_id=user.id, quest_id=quest.id))
    db.commit()
    db.refresh(user)

    return {
        "message": "XP successfully collected",
        "earned": quest.points,
        "project_points": quest.project_points,
        "total_xp": user.xp
    }



