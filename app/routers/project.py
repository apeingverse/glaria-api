from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.project import Project
from app.schemas.project_schema import ProjectCreate, ProjectUpdate, ProjectOut
from app.auth.token import get_current_user
from app.models.user import User


router = APIRouter(prefix="/projects", tags=["Projects"])

@router.post("/")
def create_project(
    project: ProjectCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    # Manual empty check
    empty_fields = []
    for field in ["name", "twitter_username", "description"]:
        value = getattr(project, field)
        if not value.strip() or value.strip().lower() == "string":
            empty_fields.append(field)

    if empty_fields:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": f"You cannot leave these fields empty: {', '.join(empty_fields)}"}
        )

    # Uniqueness check
    existing = db.query(Project).filter_by(twitter_username=project.twitter_username).first()
    if existing:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": "Twitter username already exists"}
        )

    # Save project
    new_project = Project(**project.dict())
    db.add(new_project)
    db.commit()
    db.refresh(new_project)

    return {"message": "Project successfully created", "project": ProjectOut.from_orm(new_project)}


@router.put("/{project_id}", response_model=ProjectOut)
def update_project(project_id: int, update: ProjectUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    project = db.query(Project).get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    for key, value in update.dict(exclude_unset=True).items():
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

@router.get("/", response_model=List[ProjectOut])
def get_all_projects(db: Session = Depends(get_db)):
    projects = db.query(Project).order_by(Project.created_at.desc()).all()
    return projects


@router.get("/{project_id}", response_model=ProjectOut)
def get_project_by_id(project_id: int, db: Session = Depends(get_db)):
    project = db.query(Project).get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project