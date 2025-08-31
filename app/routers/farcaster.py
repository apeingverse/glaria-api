# app/routers/farcaster.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import and_
from sqlalchemy.exc import SQLAlchemyError

from datetime import datetime, timedelta
import random
import string
import re

from eth_account.messages import encode_defunct
from eth_account import Account

from app.database import get_db
from app.models.user import User
from app.models.farcaster import FarcasterNonce
from app.auth.token import create_access_token

router = APIRouter(prefix="/farcaster", tags=["Farcaster"])

# -------------------
# Schemas
# -------------------

class FarcasterLoginRequest(BaseModel):
    fid: str
    username: str

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

class FarcasterNonceResponse(BaseModel):  # use your existing schema if you already have one
    nonce: str
    expires_at: datetime

# -------------------
# Helpers
# -------------------

def generate_nonce(length: int = 16) -> str:
    chars = string.ascii_letters + string.digits
    return "".join(random.choices(chars, k=length))

# Prefer strict FIP-11 resource URI; keep legacy as fallback
FIDS_URI_RE   = re.compile(r"farcaster://fids/(\d+)", re.IGNORECASE)
LEGACY_FID_RE = re.compile(r"\bfid\s*[:=]\s*(\d+)\b", re.IGNORECASE)

NONCE_TTL = timedelta(minutes=10)  # used only for display/logs; verification relies on expires_at

def verify_sign_in_message(message: str, signature: str) -> int:
    """
    Raw SIWF verification:
      1) EIP-191 personal_sign verification
      2) Extract FID via FIP-11 resource 'farcaster://fids/<fid>' (preferred) or legacy 'fid:<num>'
    Returns FID (int) or raises ValueError.
    """
    if not isinstance(message, str) or not message.strip():
        raise ValueError("Empty SIWF message")

    if not isinstance(signature, str) or not signature:
        raise ValueError("Invalid signature")

    sig = signature if signature.startswith("0x") else ("0x" + signature)
    # 65-byte sig => 130 hex chars + '0x' = 132 chars
    if len(sig) != 132:
        raise ValueError("Malformed signature")

    try:
        encoded = encode_defunct(text=message)
        _recovered = Account.recover_message(encoded, signature=sig)
        # (Optional) compare _recovered to stored custody/auth addresses if you enforce that
    except Exception as e:
        raise ValueError(f"Failed to recover address from signature: {str(e)}")

    m = FIDS_URI_RE.search(message) or LEGACY_FID_RE.search(message)
    if not m:
        raise ValueError("FID not found in signed message (expect 'farcaster://fids/<fid>')")

    try:
        return int(m.group(1))
    except Exception:
        raise ValueError("Invalid FID format in message")

# -------------------
# Routes
# -------------------

@router.post("/auth/flogin")
def farcaster_login(payload: FarcasterLoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter_by(farcaster_id=payload.fid).first()
    if not user:
        user = User(farcaster_id=payload.fid, username=payload.username)
        db.add(user)
        db.commit()
        db.refresh(user)

    jwt_token = create_access_token({"sub": str(user.id), "fid": payload.fid})
    return {
        "message": "Logged in via Farcaster",
        "access_token": jwt_token,
        "farcaster_id": payload.fid,
        "username": user.username,
    }

@router.post("/api/auth/farcaster-nonce", response_model=FarcasterNonceResponse)
def create_farcaster_nonce(db: Session = Depends(get_db)):
    nonce = generate_nonce(16)
    now = datetime.utcnow()
    expires_at = now + NONCE_TTL

    nonce_obj = FarcasterNonce(nonce=nonce, created_at=now, expires_at=expires_at, used=False)
    db.add(nonce_obj)
    db.commit()
    db.refresh(nonce_obj)

    return {"nonce": nonce, "expires_at": expires_at}

@router.post("/api/auth/siwf", response_model=FarcasterSIWFResponse)
def farcaster_siwf_login(payload: FarcasterSIWFRequest, db: Session = Depends(get_db)):
    nonce = payload.nonce
    message = payload.credential.message
    signature = payload.credential.signature
    now = datetime.utcnow()

    # 1) Validate nonce (exists, unused, unexpired via expires_at)
    try:
        db_nonce = (
            db.query(FarcasterNonce)
            .filter(
                and_(
                    FarcasterNonce.nonce == nonce,
                    FarcasterNonce.used == False,
                    FarcasterNonce.expires_at >= now,
                )
            )
            .with_for_update()  # ok on Postgres; if SQLite locally, remove this
            .first()
        )
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Database error while loading nonce")

    if not db_nonce:
        raise HTTPException(status_code=400, detail="Invalid, used, or expired nonce")

    # 2) Verify signature & extract FID (FIP-11 compliant)
    try:
        fid = verify_sign_in_message(message, signature)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

    # 3) Require nonce presence inside the signed message (strict match)
    if not re.search(rf"(?i)\bnonce\b\s*[:=]\s*{re.escape(str(nonce))}\b", message):
        raise HTTPException(status_code=400, detail="Nonce mismatch in message")

    # 4) Upsert user by FID; mark nonce used atomically
    try:
        user = db.query(User).filter(User.farcaster_id == fid).first()
        if not user:
            user = User(farcaster_id=fid, username=f"fc_{fid}")
            db.add(user)

        db_nonce.used = True
        db.commit()
        db.refresh(user)
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Database error while finalizing SIWF")

    # 5) Mint JWT session
    token = create_access_token({"sub": str(user.id), "fid": fid})
    return {"fid": fid, "token": token, "message": "Farcaster login successful"}