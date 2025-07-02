from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.auth.token import create_access_token, get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.user_schema import UserCreate, UserResponse

router = APIRouter(prefix="/api", tags=["User"])

@router.post("/create-profile")
def create_profile(user_data: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(
        (User.username == user_data.username) |
        (User.twitter_id == user_data.twitter_id)
    ).first()

    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists")

    user = User(
        username=user_data.username,
        email=user_data.email,
        twitter_id=user_data.twitter_id,
        twitter_username=user_data.twitter_username,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(data={"sub": str(user.id)})

    return {
        "message": "User profile successfully created",
        "access_token": token
    }


@router.delete("/delete-user/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    print(user) 
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    db.delete(user)
    db.commit()
    return {"message": f"User {user.username} deleted successfully"}



@router.get("/me")
def get_my_user_info(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "twitter_username": current_user.twitter_username,
        "xp": current_user.xp,
    }