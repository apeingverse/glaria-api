
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

# Prefer FIP-11 resource URI, but keep legacy fallback
FIDS_URI_RE = re.compile(r"farcaster://fids?/(\\d+)", re.IGNORECASE)
LEGACY_FID_RE = re.compile(r"\bfid\s*[:=]\s*(\d+)\b", re.IGNORECASE)

def verify_sign_in_message(message: str, signature: str) -> int:
    """
    Raw SIWF verification for Python backends:
      1) EIP-191 personal_sign verification
      2) Extract FID from message via FIP-11 resource URI (preferred) or legacy 'fid:123'
    Returns the integer FID or raises ValueError.
    """
    if not isinstance(message, str) or not message.strip():
        raise ValueError("Empty SIWF message")

    # Normalize signature to 0x-prefixed hex
    if not isinstance(signature, str) or not signature:
        raise ValueError("Invalid signature")
    sig = signature if signature.startswith("0x") else ("0x" + signature)

    # EIP-191 personal_sign verification (recovers an address, which you can
    # optionally compare to an allowlist of custody/auth addresses if you store them)
    try:
        encoded = encode_defunct(text=message)
        _recovered = Account.recover_message(encoded, signature=sig)
    except Exception as e:
        raise ValueError(f"Failed to recover address from signature: {str(e)}")

    # Extract FID: prefer FIP-11 resource, fallback to legacy
    m = FIDS_URI_RE.search(message) or LEGACY_FID_RE.search(message)
    if not m:
        raise ValueError("FID not found in signed message (expect 'farcaster://fids/<fid>')")

    try:
        return int(m.group(1))
    except Exception:
        raise ValueError("Invalid FID format in message")

# -------------------
# Endpoint: SIWF Login
# -------------------


NONCE_TTL = timedelta(minutes=10)

@router.post("/api/auth/siwf", response_model=FarcasterSIWFResponse)
def farcaster_siwf_login(payload: FarcasterSIWFRequest, db: Session = Depends(get_db)):
    nonce = payload.nonce
    message = payload.credential.message
    signature = payload.credential.signature

    # 1) Validate nonce (exists, unused, unexpired)
    now = datetime.utcnow()
    db_nonce = (
        db.query(FarcasterNonce)
        .filter(
            and_(
                FarcasterNonce.nonce == nonce,
                FarcasterNonce.used == False,
                FarcasterNonce.created_at >= (now - NONCE_TTL),
            )
        )
        .with_for_update()  # if supported
        .first()
    )
    if not db_nonce:
        raise HTTPException(status_code=400, detail="Invalid, used, or expired nonce")

    # 2) Verify signature & extract FID (FIP-11 compliant)
    try:
        fid = verify_sign_in_message(message, signature)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

    # 3) Require nonce to be present within the signed message
    if str(nonce) not in message:
        raise HTTPException(status_code=400, detail="Nonce mismatch in message")

    # 4) Upsert user by FID; mark nonce used atomically
    user = db.query(User).filter(User.farcaster_id == fid).first()
    if not user:
        user = User(farcaster_id=fid, username=f"fc_{fid}")
        db.add(user)

    db_nonce.used = True
    db.commit()
    db.refresh(user)

    # 5) Mint JWT session
    token = create_access_token({"sub": str(user.id), "fid": fid})

    return {"fid": fid, "token": token, "message": "Farcaster login successful"}