# app/auth/token.py
from __future__ import annotations

from datetime import datetime, timedelta
import os
from typing import Optional

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.farcaster import FarcasterUser
from app.core.config import settings

# Key/alg
SECRET_KEY = os.getenv("SECRET_KEY") or settings.JWT_SECRET
ALGORITHM = settings.JWT_ALG
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "10080"))  # 7 days default

security = HTTPBearer(auto_error=False)  # don't auto-fail if no header


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> FarcasterUser:
    """
    Resolve current user from:
      1) Authorization: Bearer <token>  (Twitter flow, manual testing)
      2) Cookie: settings.SESSION_COOKIE_NAME (Farcaster cookie session)
    """
    token = credentials.credentials if credentials else request.cookies.get(settings.SESSION_COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        fid = payload.get("sub")
        if fid is None:
            raise HTTPException(status_code=401, detail="Invalid token payload")
        user = db.query(FarcasterUser).filter(FarcasterUser.fid == int(fid)).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user
    except JWTError:
        raise HTTPException(status_code=403, detail="Could not validate credentials")
