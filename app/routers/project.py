from typing import List, Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.project import Project
from app.models.quests import Quest
from app.models.user_project_xp import UserProjectXP
from app.schemas.project_schema import ProjectCreate, ProjectListItem, ProjectUpdate, ProjectOut
from app.auth.token import get_current_user
from app.models.user import User
from app.utils.s3 import upload_image_to_s3


router = APIRouter(prefix="/projects", tags=["Projects"])

@router.post("/")
def create_project(
    name: str = Form(...),
    twitter_username: str = Form(...),
    description: str = Form(...),
    discord_url: Optional[str] = Form(None),
    telegram_url: Optional[str] = Form(None),
    twitter_url: Optional[str] = Form(None),
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    # Manual empty check
    empty_fields = []
    for field_name, value in {
        "name": name,
        "twitter_username": twitter_username,
        "description": description
    }.items():
        if not value.strip() or value.strip().lower() == "string":
            empty_fields.append(field_name)

    if empty_fields:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": f"You cannot leave these fields empty: {', '.join(empty_fields)}"}
        )

    # Uniqueness check
    existing = db.query(Project).filter_by(twitter_username=twitter_username).first()
    if existing:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": "Twitter username already exists"}
        )

    # Upload image to S3
    image_url = upload_image_to_s3(image)

    # Save project
    new_project = Project(
        name=name.strip(),
        twitter_username=twitter_username.strip(),
        description=description.strip(),
        image_url=image_url,
        discord_url=discord_url,
        telegram_url=telegram_url,
        twitter_url=twitter_url
    )
    db.add(new_project)
    db.commit()
    db.refresh(new_project)

    return {"message": "Project successfully created", "project": ProjectOut.from_orm(new_project)}


@router.put("/{project_id}", response_model=ProjectOut)
def update_project(
    project_id: int,
    name: Optional[str] = Form(None),
    twitter_username: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    discord_url: Optional[str] = Form(None),
    telegram_url: Optional[str] = Form(None),
    twitter_url: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    project = db.query(Project).get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Upload new image if provided
    if image:
        image_url = upload_image_to_s3(image)
        project.image_url = image_url

    # Update other fields if provided
    for key, value in {
        "name": name,
        "twitter_username": twitter_username,
        "description": description,
        "discord_url": discord_url,
        "telegram_url": telegram_url,
        "twitter_url": twitter_url
    }.items():
        if value is not None:
            setattr(project, key, value)

    db.commit()
    db.refresh(project)
    return project

@router.delete("/{project_id}")
def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    project = db.query(Project).get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    project_name = project.name
    db.delete(project)
    db.commit()

    return {"message": f"Project {project_name} was successfully deleted"}

@router.get("/", response_model=List[ProjectListItem])
def get_all_projects(db: Session = Depends(get_db)):
    projects = db.query(Project).all()
    return projects


@router.get("/{project_id}", response_model=ProjectOut)
def get_project_by_id(project_id: int, db: Session = Depends(get_db)):
    project = db.query(Project).get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project



@router.get("/xp-by-project/{project_id}")
def xp_by_project(
    project_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    # Get total project XP from all quests
    total_project_xp = db.query(func.coalesce(func.sum(Quest.project_points), 0)).filter(
        Quest.project_id == project_id
    ).scalar()

    # Get user's claimed XP for that project
    user_xp_row = db.query(UserProjectXP).filter_by(
        user_id=user.id, project_id=project_id
    ).first()
    claimed_xp = user_xp_row.xp if user_xp_row else 0

    return {
        "project_id": project_id,
        "total_project_xp": total_project_xp,
        "user_claimed_xp": claimed_xp
    }


@router.get("/projects/{project_id}/leaderboard")
def get_project_leaderboard(project_id: int, db: Session = Depends(get_db)):
    results = (
        db.query(
            User.twitter_username,
            User.nft_image_url,
            UserProjectXP.xp
        )
        .join(UserProjectXP, User.id == UserProjectXP.user_id)
        .filter(UserProjectXP.project_id == project_id)
        .order_by(UserProjectXP.xp.desc())
        .all()
    )

    def mask_username(username: str) -> str:
        return username[:2] + "**" if len(username) >= 3 else "*" * len(username)

    return [
        {
            "twitter_username": mask_username(r.twitter_username),
            "nft_image_url": r.nft_image_url,
            "project_xp": r.xp
        }
        for r in results
    ]