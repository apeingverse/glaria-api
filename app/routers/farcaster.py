# app/routers/farcaster.py
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import select, update, and_, func

from app.database import get_db
from app.models.farcaster import FarcasterNonce, FarcasterUser
from app.services.siwf import verify_message_and_get
from app.auth.token import create_access_token, get_current_user

import secrets
import string

router = APIRouter(prefix="/farcaster", tags=["farcaster"])

ALPHANUM = string.ascii_letters + string.digits


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _make_nonce(n: int = 24) -> str:
    return "".join(secrets.choice(ALPHANUM) for _ in range(n))


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


# ---------- Routes ----------
@router.get("/nonce", response_model=NonceOut)
def get_nonce(db: Session = Depends(get_db)):
    """Issue a server nonce (single-use, 15m TTL)."""
    nonce = _make_nonce(24)
    ttl_secs = 15 * 60
    db.add(
        FarcasterNonce(
            nonce=nonce,
            used=False,
            expires_at=_utcnow() + timedelta(seconds=ttl_secs),
        )
    )
    db.commit()
    return NonceOut(nonce=nonce, expires_in=ttl_secs)


@router.post("/siwf", response_model=VerifyOut)
def siwf_verify(payload: VerifyIn, db: Session = Depends(get_db), response: Response = None):
    """
    Verify SIWF (Farcaster):
      - Verify SIWE/SIWF (domain, nonce, chainId=10)
      - Atomically consume server-issued nonce if fresh & unused
      - Upsert FarcasterUser and mint JWT
      - Return token in JSON AND set HttpOnly cookie
    """
    # 1) Verify SIWF message
    try:
        verified = verify_message_and_get(
            fid_expected=payload.fid,
            message=payload.message,
            signature=payload.signature,
            expected_nonce=None,  # or your FarcasterNonce if you wire it up
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    fid = verified["fid"]
    signer = verified["signer"]
    signed_nonce = verified["nonce"]
    domain = verified["domain"]

    # 2) Atomically mark nonce used (only if you're issuing nonces)
    result = db.execute(
        update(FarcasterNonce)
        .where(
            and_(
                FarcasterNonce.nonce == signed_nonce,
                FarcasterNonce.used.is_(False),
                FarcasterNonce.expires_at > func.now(),
            )
        )
        .values(used=True, fid=fid)
    )
    if result.rowcount != 1:
        db.rollback()
        raise HTTPException(status_code=400, detail="Nonce invalid, expired, or already used")

    # 3) Upsert FarcasterUser
    user = db.execute(
        select(FarcasterUser).where(FarcasterUser.fid == fid)
    ).scalar_one_or_none()

    if not user:
        user = FarcasterUser(
            fid=fid,
            custody_address=signer,
            username=payload.username,
            display_name=payload.display_name,
            pfp_url=payload.pfp_url,
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

    # Also set HttpOnly cookie (optional if you rely on localStorage)
    if response is not None:
        response.set_cookie(
            key="access_token",
            value=token,
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=60 * 60 * 24 * 30,  # 30 days
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
