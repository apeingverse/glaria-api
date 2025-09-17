from fastapi import APIRouter, Form, UploadFile, File, Depends, HTTPException, status, Response
from fastapi.responses import JSONResponse
from typing import Optional, List, Any
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import func, select
from pydantic import BaseModel
from app.database import get_db
from app.auth.token import get_current_user
from app.models.farcaster import (
    FarcasterProject, FarcasterQuest, FarcasterUser, FarcasterUserCompletedQuest
)
from app.schemas.farcaster import ProjectOut, ProjectListItem
from app.utils.s3 import upload_image_to_s3
from app.services.siwf import verify_message_and_get
from app.core.config import settings
from app.auth.token import create_access_token

router = APIRouter(prefix="/farcaster", tags=["farcaster"])


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class VerifyIn(BaseModel):
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
    raw = _ensure_raw_siwe(payload.message)
    try:
        verified = verify_message_and_get(
            fid_expected=payload.fid,
            message=raw,
            signature=payload.signature,
            expected_nonce=None,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    fid = verified["fid"]
    signer = verified["signer"]
    domain = verified["domain"]

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

    claims = {"sub": str(user.fid), "addr": signer, "dom": domain}
    token = create_access_token(claims)

    if response is not None:
        max_age = settings.ACCESS_TOKEN_EXPIRES_MINUTES * 60
        samesite = settings.SESSION_COOKIE_SAMESITE
        secure = settings.SESSION_COOKIE_SECURE or (samesite.lower() == "none")

        response.set_cookie(
            key=settings.SESSION_COOKIE_NAME,
            value=token,
            httponly=True,
            secure=secure,
            samesite=samesite,
            domain=settings.SESSION_COOKIE_DOMAIN,
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


@router.post("/")
def create_project(
    name: str = Form(...),
    farcaster_username: str = Form(...),
    description: str = Form(...),
    discord_url: Optional[str] = Form(None),
    telegram_url: Optional[str] = Form(None),
    twitter_url: Optional[str] = Form(None),
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: FarcasterUser = Depends(get_current_user)
):
    empty_fields = [
        field for field, value in {
            "name": name,
            "farcaster_username": farcaster_username,
            "description": description
        }.items() if not value.strip() or value.strip().lower() == "string"
    ]
    if empty_fields:
        return JSONResponse(status_code=400, content={"message": f"Empty fields: {', '.join(empty_fields)}"})

    existing = db.query(FarcasterProject).filter_by(farcaster_username=farcaster_username).first()
    if existing:
        return JSONResponse(status_code=400, content={"message": "Username already has a project"})

    image_url = upload_image_to_s3(image)

    new_project = FarcasterProject(
        name=name.strip(),
        farcaster_username=farcaster_username.strip(),
        description=description.strip(),
        image_url=image_url,
        discord_url=discord_url,
        telegram_url=telegram_url,
        twitter_url=twitter_url,
        farcaster_user_id=user.id,
        fid=user.fid
    )
    db.add(new_project)
    db.commit()
    db.refresh(new_project)

    return {"message": "Project created", "project": ProjectOut.from_orm(new_project)}


@router.put("/{project_id}", response_model=ProjectOut)
def update_project(
    project_id: int,
    name: Optional[str] = Form(None),
    farcaster_username: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    discord_url: Optional[str] = Form(None),
    telegram_url: Optional[str] = Form(None),
    twitter_url: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    user: FarcasterUser = Depends(get_current_user)
):
    project = db.query(FarcasterProject).get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project.farcaster_user_id != user.id:
        raise HTTPException(status_code=403, detail="Unauthorized")

    if image:
        project.image_url = upload_image_to_s3(image)

    for field, value in {
        "name": name,
        "farcaster_username": farcaster_username,
        "description": description,
        "discord_url": discord_url,
        "telegram_url": telegram_url,
        "twitter_url": twitter_url
    }.items():
        if value is not None:
            setattr(project, field, value)

    db.commit()
    db.refresh(project)
    return project


@router.delete("/{project_id}")
def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    user: FarcasterUser = Depends(get_current_user)
):
    project = db.query(FarcasterProject).get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.farcaster_user_id != user.id:
        raise HTTPException(status_code=403, detail="Unauthorized")

    db.delete(project)
    db.commit()
    return {"message": f"Project '{project.name}' deleted"}


@router.get("/", response_model=List[ProjectListItem])
def get_all_projects(db: Session = Depends(get_db)):
    return db.query(FarcasterProject).all()


@router.get("/{project_id}", response_model=ProjectOut)
def get_project_by_id(project_id: int, db: Session = Depends(get_db)):
    project = db.query(FarcasterProject).get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.get("/xp-by-project/{project_id}")
def xp_by_project(
    project_id: int,
    db: Session = Depends(get_db),
    user: FarcasterUser = Depends(get_current_user)
):
    total_xp = db.query(func.coalesce(func.sum(FarcasterQuest.points), 0)).filter(
        FarcasterQuest.project_id == project_id
    ).scalar()

    user_xp = db.query(func.coalesce(func.sum(FarcasterQuest.points), 0)).join(
        FarcasterUserCompletedQuest, FarcasterUserCompletedQuest.quest_id == FarcasterQuest.id
    ).filter(
        FarcasterUserCompletedQuest.farcaster_user_id == user.id,
        FarcasterQuest.project_id == project_id
    ).scalar()

    return {
        "project_id": project_id,
        "total_project_xp": total_xp,
        "user_claimed_xp": user_xp
    }


"""
@router.get("/{project_id}/leaderboard")
def get_project_leaderboard(project_id: int, db: Session = Depends(get_db)):
    results = (
        db.query(
            FarcasterUser.username,
            FarcasterUser.pfp_url,
            func.coalesce(func.sum(FarcasterQuest.points), 0).label("xp")
        )
        .join(FarcasterUserCompletedQuest, FarcasterUser.id == FarcasterUserCompletedQuest.farcaster_user_id)
        .join(FarcasterQuest, FarcasterQuest.id == FarcasterUserCompletedQuest.quest_id)
        .filter(FarcasterQuest.project_id == project_id)
        .group_by(FarcasterUser.id)
        .order_by(func.sum(FarcasterQuest.points).desc())
        .all()
    )

    def mask_username(username: str) -> str:
        return username[:2] + "**" if username and len(username) >= 3 else "*" * len(username or "")

    return [
        {
            "username": mask_username(r.username),
            "pfp_url": r.pfp_url,
            "project_xp": r.xp
        } for r in results
    ]
    """