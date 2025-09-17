from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from app.database import get_db
from app.auth.token import get_current_user
from app.models.farcaster import (
    FarcasterQuest,
    FarcasterUserCompletedQuest,
    FarcasterUser,
)
from app.schemas.farcaster import QuestClaimRequest, QuestClaimResponse
from app.services.farcaster_api import (
    has_liked_cast,
    has_recasted_cast,
    has_replied_to_cast,
    has_followed_user,
)

router = APIRouter(prefix="/farcaster", tags=["Farcaster Claim"])

@router.post("/claimpoints", response_model=QuestClaimResponse)
def claim_points(
    payload: QuestClaimRequest,
    db: Session = Depends(get_db),
    user: FarcasterUser = Depends(get_current_user),
):
    # 1. Lookup quest
    quest = db.query(FarcasterQuest).get(payload.quest_id)
    if not quest:
        raise HTTPException(status_code=404, detail="Quest not found")

    # 2. Prevent duplicate claims
    existing = db.query(FarcasterUserCompletedQuest).filter_by(
        farcaster_user_id=user.id,
        quest_id=quest.id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Quest already claimed")

    # 3. Validate action
    quest_type = quest.type.lower()
    is_valid = False

    if quest_type == "like":
        is_valid = has_liked_cast(user.fid, quest.target_url)
    elif quest_type == "recast":
        is_valid = has_recasted_cast(user.fid, quest.target_url)
    elif quest_type == "reply":
        is_valid = has_replied_to_cast(user.fid, quest.target_url)
    elif quest_type == "follow":
        is_valid = has_followed_user(user.fid, quest.target_url)
    else:
        raise HTTPException(status_code=400, detail="Unsupported quest type")

    if not is_valid:
        raise HTTPException(status_code=400, detail="Quest action not verified")

    # 4. Mark as completed
    completion = FarcasterUserCompletedQuest(
        user_id=user.id,
        quest_id=quest.id,
        project_id=quest.project_id,
        completed_at=datetime.utcnow(),
        quest_type=quest_type,
    )
    db.add(completion)
    db.commit()

    return QuestClaimResponse(
        success=True,
        message="Quest verified and points claimed",
        points_awarded=quest.points,
    )