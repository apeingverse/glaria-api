# app/routers/farcaster.py
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError

from app.database import get_db
from app.models.farcaster import FarcasterNonce, FarcasterUser
from app.services.siwf import verify_message_and_get
from app.auth.token import create_access_token, get_current_user

router = APIRouter(prefix="/farcaster", tags=["farcaster"])

def _utcnow() -> datetime:
    return datetime.now(timezone.utc)

# ---------- Schemas ----------
class NonceOut(BaseModel):
    nonce: str
    expires_in: int  # seconds

class VerifyIn(BaseModel):
    message: str
    signature: str
    fid: Optional[int] = None
    username: Optional[str] = None
    display_name: Optional[str] = None
    pfp_url: Optional[str] = None

class VerifyOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    fid: int
    custody_address: str

# (Optional) keep this if you still want a server-issued nonce endpoint
@router.get("/nonce", response_model=NonceOut)
def get_nonce():
    # You can keep or remove this. MiniKit doesn't use it.
    # Provided only for compatibility / future clients.
    ttl_secs = 15 * 60
    # Not inserting here anymore; we now "tombstone on insert" after verify.
    return NonceOut(nonce="(client_generated)", expires_in=ttl_secs)

@router.post("/siwf", response_model=VerifyOut)
def siwf_verify(payload: VerifyIn, db: Session = Depends(get_db), response: Response = None):
    """
    Verify SIWF (Farcaster):
      - Verify SIWE/SIWF (domain, chainId=10, signature, custody)
      - **Tombstone the SIWE nonce on first use** (unique insert = replay protection)
      - Upsert FarcasterUser and mint JWT
      - Return token in JSON AND set HttpOnly cookie
    """
    # 1) Verify cryptographically + domain/chain/fid
    try:
        verified = verify_message_and_get(
            fid_expected=payload.fid,
            message=payload.message,
            signature=payload.signature,
            expected_nonce=None,   # we don't pre-issue; accept MiniKit nonce
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    fid          = verified["fid"]
    signer       = verified["signer"]
    signed_nonce = verified["nonce"]
    domain       = verified["domain"]

    # 2) Replay protection: "consume on insert" using a UNIQUE(nonce) constraint
    # If this INSERT fails with IntegrityError, the nonce was already used.
    try:
        db.add(
            FarcasterNonce(
                nonce=signed_nonce,
                used=True,                        # mark it used immediately
                fid=fid,
                expires_at=_utcnow() + timedelta(minutes=30),
            )
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Nonce invalid, expired, or already used")

    # 3) Upsert FarcasterUser
    user = db.execute(
        select(FarcasterUser).where(FarcasterUser.fid == fid)
    ).scalar_one_or_none()

    now = _utcnow()
    if not user:
        user = FarcasterUser(
            fid=fid,
            custody_address=signer,
            username=payload.username,
            display_name=payload.display_name,
            pfp_url=payload.pfp_url,
            created_at=now,
        )
        db.add(user)
    else:
        user.custody_address = signer
        if payload.username is not None:
            user.username = payload.username
        if payload.display_name is not None:
            user.display_name = payload.display_name
        if payload.pfp_url is not None:
            user.pfp_url = payload.pfp_url

    db.commit()

    # 4) Mint JWT
    token = create_access_token(
        sub=str(user.fid),
        extra={"addr": signer, "dom": domain},
    )

    # 5) Set HttpOnly cookie
    if response is not None:
        response.set_cookie(
            key="access_token",
            value=token,
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=60 * 60 * 24 * 30,
        )

    return VerifyOut(access_token=token, fid=user.fid, custody_address=signer)

@router.get("/me")
def me(current_user: FarcasterUser = Depends(get_current_user)):
    return {
        "fid": current_user.fid,
        "custody_address": current_user.custody_address,
        "username": current_user.username,
        "display_name": current_user.display_name,
        "pfp_url": current_user.pfp_url,
    }

@router.post("/logout")
def logout(response: Response):
    """Clear the auth cookie."""
    response.delete_cookie(key="access_token")
    return {"detail": "Logged out"}
