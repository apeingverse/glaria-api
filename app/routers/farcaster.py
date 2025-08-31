
from pydantic import BaseModel

class FarcasterLoginRequest(BaseModel):
    fid: str       # Farcaster ID
    username: str  # optional display name or handle


from fastapi import APIRouter, Depends, HTTPException
from app.database import get_db
from sqlalchemy.orm import Session
from app.models.user import User
from app.auth.token import create_access_token
import uuid
from datetime import datetime, timedelta

from app.models.farcaster import FarcasterNonce
from app.database import get_db
from app.schemas.farcaster import FarcasterNonceResponse  # if using pydantic

router = APIRouter(prefix="/farcaster", tags=["Farcaster"])




@router.post("/auth/flogin")
def farcaster_login(payload: FarcasterLoginRequest, db: Session = Depends(get_db)):
    # Check if user already exists
    user = db.query(User).filter_by(farcaster_id=payload.fid).first()
    
    if not user:
        # Create new user
        user = User(farcaster_id=payload.fid, username=payload.username)
        db.add(user)
        db.commit()
        db.refresh(user)

    # Create JWT token for frontend
    jwt_token = create_access_token(data={"sub": str(user.id)})

    return {
        "message": "Logged in via Farcaster",
        "access_token": jwt_token,
        "farcaster_id": payload.fid,
        "username": user.username
    }



@router.post("/api/auth/farcaster-nonce", response_model=FarcasterNonceResponse)
def create_farcaster_nonce(db: Session = Depends(get_db)):
    # Generate a random nonce
    nonce = str(uuid.uuid4())
    expires_at = datetime.utcnow() + timedelta(minutes=10)  # nonce expires in 10 mins

    # Save to DB
    nonce_obj = FarcasterNonce(nonce=nonce, expires_at=expires_at, used=False)
    db.add(nonce_obj)
    db.commit()
    db.refresh(nonce_obj)

    return {"nonce": nonce, "expires_at": expires_at}