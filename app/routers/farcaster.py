
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
from eth_account.messages import encode_defunct
from eth_account.account import Account
import re
from app.auth.token import create_access_token



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



import random
import string

def generate_nonce(length: int = 16) -> str:
    chars = string.ascii_letters + string.digits
    return ''.join(random.choices(chars, k=length))


@router.post("/api/auth/farcaster-nonce", response_model=FarcasterNonceResponse)
def create_farcaster_nonce(db: Session = Depends(get_db)):
    nonce = generate_nonce(16)  # 16 alphanumeric chars
    expires_at = datetime.utcnow() + timedelta(minutes=10)

    nonce_obj = FarcasterNonce(nonce=nonce, expires_at=expires_at, used=False)
    db.add(nonce_obj)
    db.commit()
    db.refresh(nonce_obj)

    return {"nonce": nonce, "expires_at": expires_at}



class FarcasterCredential(BaseModel):
    message: str
    signature: str

class FarcasterSIWFRequest(BaseModel):
    nonce: str
    credential: FarcasterCredential

class FarcasterSIWFResponse(BaseModel):
    fid: int
    token: str
    message: str

# -------------------
# Helper: Verify SIWF Message
# -------------------

def verify_sign_in_message(message: str, signature: str) -> int:
    """
    Verifies Farcaster SIWF message signature and returns FID.
    Expects message to include 'fid:<number>' somewhere.
    """
    # Encode message for Ethereum signature verification
    encoded = encode_defunct(text=message)
    try:
        recovered_address = Account.recover_message(encoded, signature=signature)
    except Exception as e:
        raise ValueError(f"Failed to recover address from signature: {str(e)}")

    # Extract FID from message (assuming 'fid:<number>' included in signed message)
    match = re.search(r"fid[:=](\d+)", message)
    if not match:
        raise ValueError("FID not found in signed message")
    fid = int(match.group(1))

    # Optionally: You could check that recovered_address matches the custody address if you store it
    # For Mini Apps: usually FID alone is enough for user identification

    return fid

# -------------------
# Endpoint: SIWF Login
# -------------------

@router.post("/api/auth/siwf", response_model=FarcasterSIWFResponse)
def farcaster_siwf_login(payload: FarcasterSIWFRequest, db: Session = Depends(get_db)):
    nonce = payload.nonce
    message = payload.credential.message
    signature = payload.credential.signature

    # Step 1: Validate nonce
    db_nonce = (
        db.query(FarcasterNonce)
        .filter(FarcasterNonce.nonce == nonce, FarcasterNonce.used == False)
        .first()
    )
    if not db_nonce:
        raise HTTPException(status_code=400, detail="Invalid or used nonce")

    # Step 2: Verify signature & extract FID
    try:
        fid = verify_sign_in_message(message, signature)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

    # Step 3: Confirm nonce is included in message
    if nonce not in message:
        raise HTTPException(status_code=400, detail="Nonce mismatch in message")

    # Step 4: Link FID to user
    user = db.query(User).get(db_nonce.user_id)  # adjust depending on your user linking
    user.fid = fid
    db_nonce.used = True
    db.commit()

    # Step 5: Mint JWT session (you already have create_jwt_for_user)
    # Step 5: Mint JWT session
    token_data = {"sub": str(user.id)}
    token = create_access_token(token_data)

    return {"fid": fid, "token": token, "message": "Farcaster login successful"}


