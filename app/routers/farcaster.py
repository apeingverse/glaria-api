# app/routers/farcaster.py
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.database import get_db
from app.models.farcaster import FarcasterUser
from app.services.siwf import verify_message_and_get
from app.auth.token import create_access_token, get_current_user
from app.core.config import settings

router = APIRouter(prefix="/farcaster", tags=["farcaster"])


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class VerifyIn(BaseModel):
    message: Any   # MiniKit can wrap this; normalize below
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
    Normalize 'message' to the raw SIWE multi-line string.
    Supports:
      - "...."
      - {"message": "..."}
      - {"value": {"message": "..."}}
    """
    if isinstance(msg, str):
        return msg
    if isinstance(msg, dict):
        m = msg.get("message")
        if isinstance(m, str):
            return m
        v = msg.get("value")
        if isinstance(v, dict):
            mv = v.get("message")
            if isinstance(mv, str):
                return mv
    raise HTTPException(status_code=400, detail="Malformed SIWE payload: 'message' must be a string")


@router.post("/siwf", response_model=VerifyOut)
def siwf_verify(payload: VerifyIn, db: Session = Depends(get_db), response: Response = None):
    # 1) Normalize + verify SIWF
    raw = _ensure_raw_siwe(payload.message)
    try:
        verified = verify_message_and_get(
            fid_expected=payload.fid,
            message=raw,
            signature=payload.signature,
            expected_nonce=None,  # not enforcing server nonce in this flow
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    fid = verified["fid"]
    signer = verified["signer"]
    domain = verified["domain"]

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

    # 3) Mint JWT (dict-style, compatible with your helper)
    claims = {"sub": str(user.fid), "addr": signer, "dom": domain}
    token = create_access_token(claims)

    # 4) HttpOnly cookie session
    if response is not None:
        max_age = settings.ACCESS_TOKEN_EXPIRES_MINUTES * 60
        # If you set SameSite=None, cookie MUST be Secure
        samesite = settings.SESSION_COOKIE_SAMESITE
        secure = settings.SESSION_COOKIE_SECURE or (samesite.lower() == "none")

        response.set_cookie(
            key=settings.SESSION_COOKIE_NAME,
            value=token,
            httponly=True,
            secure=secure,
            samesite=samesite,
            domain=settings.SESSION_COOKIE_DOMAIN,  # e.g. ".glaria.xyz" to share across subdomains
            max_age=max_age,
            expires=max_age,
            path="/",
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
    response.delete_cookie(
        key=settings.SESSION_COOKIE_NAME,
        domain=settings.SESSION_COOKIE_DOMAIN,
        path="/",
    )
    return {"detail": "Logged out"}
