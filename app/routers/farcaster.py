# app/routers/farcaster.py
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.database import get_db
from app.models.farcaster import FarcasterUser
from app.services.siwf import verify_message_and_get
from app.auth.token import create_access_token, get_current_user

router = APIRouter(prefix="/farcaster", tags=["farcaster"])

def _utcnow() -> datetime:
    return datetime.now(timezone.utc)

# ---------- Schemas ----------
class VerifyIn(BaseModel):
    # Accept ANY so we can unwrap dict shapes from different MiniKit versions
    message: Any
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

def _ensure_raw_siwe(msg: Any) -> str:
    """
    Normalizes the 'message' field to the raw multi-line SIWE string.
    Handles shapes like:
      - "...." (string)
      - {"message": "..."}
      - {"value": {"message": "..."}}
    """
    if isinstance(msg, str):
        return msg
    if isinstance(msg, dict):
        if isinstance(msg.get("message"), str):
            return msg["message"]  # mini SDKs sometimes wrap once
        val = msg.get("value")
        if isinstance(val, dict) and isinstance(val.get("message"), str):
            return val["message"]  # mini SDKs sometimes wrap twice
    raise HTTPException(status_code=400, detail="Malformed SIWE payload: 'message' must be a string")

# ---------- Routes ----------
@router.post("/siwf", response_model=VerifyOut)
def siwf_verify(payload: VerifyIn, db: Session = Depends(get_db), response: Response = None):
    """
    Verify SIWF (Farcaster):
      - Parse & verify SIWE (domain exact, chainId=10, signature)
      - Upsert FarcasterUser and mint JWT
      - Return token in JSON AND set HttpOnly cookie
    """
    # 1) Normalize + Verify
    raw = _ensure_raw_siwe(payload.message)
    try:
        verified = verify_message_and_get(
            fid_expected=payload.fid,
            message=raw,
            signature=payload.signature,
            expected_nonce=None,   # no server nonce enforcement right now
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    fid         = verified["fid"]
    signer      = verified["signer"]
    domain      = verified["domain"]

    # 2) Upsert FarcasterUser
    user = db.execute(select(FarcasterUser).where(FarcasterUser.fid == fid)).scalar_one_or_none()

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

    # 3) Mint JWT
    token = create_access_token(
        sub=str(user.fid),
        extra={"addr": signer, "dom": domain},
    )

    # 4) Set HttpOnly cookie (optional)
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
