from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from app.database import get_db
from app.models.farcaster import (
    FarcasterQuest,
    FarcasterUserCompletedQuest,
    FarcasterUser,
)
from app.schemas.farcaster import QuestClaimRequest, QuestClaimResponse
from app.auth.token import get_current_user

# Verification helpers (now using Neynar)
from app.services.farcaster_api import (
    has_liked_cast,
    has_recasted_cast,
    has_replied_to_cast,
    has_followed_user,
)

router = APIRouter(prefix="/farcaster", tags=["Farcaster"])

@router.post("/claimpoints", response_model=QuestClaimResponse)
def claim_points(
    payload: QuestClaimRequest,
    db: Session = Depends(get_db),
    user: FarcasterUser = Depends(get_current_user),
):
    # 1. Get quest
    quest = db.query(FarcasterQuest).get(payload.quest_id)
    if not quest:
        raise HTTPException(status_code=404, detail="Quest not found")

    # 2. Check for duplicate claims
    existing = db.query(FarcasterUserCompletedQuest).filter_by(
        farcaster_user_id=user.id,
        quest_id=quest.id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="You already claimed this quest.")

    # 3. Verify quest action via Neynar
    quest_type = quest.type.lower()
    is_valid = False

    try:
        if quest_type == "like":
            is_valid = has_liked_cast(user.fid, quest.target_url)
        elif quest_type == "recast":
            is_valid = has_recasted_cast(user.fid, quest.target_url)
        elif quest_type == "reply":
            is_valid = has_replied_to_cast(user.fid, quest.target_url)
        elif quest_type == "follow":
            is_valid = has_followed_user(user.fid, quest.target_url)
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported quest type: {quest_type}")
    except Exception as e:
        print(f"[claim_points] Error verifying quest ({quest_type}) for fid={user.fid} at URL={quest.target_url} — {e}")
        raise HTTPException(status_code=500, detail="Error verifying quest. Try again later.")

    if not is_valid:
        raise HTTPException(status_code=400, detail="Action not verified. Make sure you completed the quest.")

    # 4. Save completion
    completion = FarcasterUserCompletedQuest(
        farcaster_user_id=user.id,
        quest_id=quest.id,
        quest_type=quest_type,
        completed_at=datetime.utcnow()
    )
    db.add(completion)
    db.commit()
    db.refresh(completion)  # Optional: if you want to return ID later

    return QuestClaimResponse(
        success=True,
        message="✅ Quest verified and points claimed!"
    )