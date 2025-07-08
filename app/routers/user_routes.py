import os
from typing import Optional
from click import prompt
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.auth.token import create_access_token, get_current_user
from app.database import get_db
from app.models.user import User
from app.models.user_project_xp import UserProjectXP
from app.schemas.user_schema import UserCreate, UserResponse
import requests
from sqlalchemy import desc

from app.utils.s3 import upload_image_bytes_to_s3

router = APIRouter(prefix="/api", tags=["User"])


class LeaderboardUser(BaseModel):
    twitter_username: str
    nft_image_url: Optional[str]
    total_xp: int

    model_config = {"from_attributes": True}



@router.get("/leaderboard", response_model=list[LeaderboardUser])
def get_leaderboard(db: Session = Depends(get_db)):
    users = (
        db.query(User)
        .order_by(desc(User.xp))
        .limit(100)
        .all()
    )

    return [
        LeaderboardUser(
            twitter_username=user.twitter_username,
            nft_image_url=user.nft_image_url,
            total_xp=user.xp
        )
        for user in users
    ]





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
        nft_image_url=user_data.nft_image_url  # <-- Save to DB
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
        "profile_image": current_user.nft_image_url
    }



DEEPAI_API_KEY = os.getenv("DEEPAI_API_KEY")  # store this in your .env

@router.post("/generate-nft")
def generate_nft_image(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    print("📤 Sending request to DeepAI...")
    prompt = f"{user.username}'s Web3 NFT avatar"
    print("📤 Prompt for DeepAI:", prompt)
    # 1. Generate image from DeepAI
    response = requests.post(
        "https://api.deepai.org/api/text2img",
        data={'text': prompt},
        headers={'api-key': DEEPAI_API_KEY}
    )

    print("📥 DeepAI Response:", response.status_code, response.text)

    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="Failed to generate image")

    image_url = response.json().get('output_url')
    if not image_url:
        raise HTTPException(status_code=500, detail="No image returned")

    # 2. Download the image
    image_data = requests.get(image_url).content
    s3_url = upload_image_bytes_to_s3(image_data, f"nfts/{user.id}.png")

    # 3. Save to DB
    user.nft_image_url = s3_url
    db.commit()
    db.refresh(user)

    return {"message": "NFT generated and saved", "nft_image_url": s3_url}