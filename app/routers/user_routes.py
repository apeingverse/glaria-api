from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.auth.token import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.user_schema import UserCreate, UserResponse

router = APIRouter(prefix="/api", tags=["User"])

@router.post("/create-profile")
def create_profile(user: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == user.username).first():
        raise HTTPException(status_code=400, detail="Username already taken")

    new_user = User(
        username=user.username,
        email=user.email,
        twitter_id=user.twitter_id,
        twitter_username=user.twitter_username,
        wallet_address=user.wallet_address,
        xp=100
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {"status": "profile_created", "user_id": new_user.id}




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