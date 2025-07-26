from datetime import datetime
import string
from urllib.parse import urlencode
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from starlette.responses import JSONResponse
import httpx, base64, os
from dotenv import load_dotenv
from sqlalchemy.orm import Session
import random
from app.models.nonce import WalletNonce 
from app.database import get_db
from app.models.twitter_token import TwitterToken
from app.models.user import User

from app.auth.token import create_access_token

from eth_account.messages import defunct_hash_message
from eth_account import Account


from eth_account.messages import encode_defunct
load_dotenv()
router = APIRouter()

client_id = os.getenv("TWITTER_CLIENT_ID")
client_secret = os.getenv("TWITTER_CLIENT_SECRET")
redirect_uri = os.getenv("TWITTER_CALLBACK_URL")
verifier_store = {} 

# temp verifier store
verifier_store = {}

@router.get("/auth/twitter/login")
def twitter_login():
    import secrets, hashlib, base64
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()
    ).decode().rstrip("=")
    state = secrets.token_urlsafe(16)
    verifier_store[state] = verifier

    return RedirectResponse(
        f"https://twitter.com/i/oauth2/authorize?"
        f"response_type=code"
        f"&client_id={client_id}"
        f"&redirect_uri={redirect_uri}"
        f"&scope=users.read%20tweet.read%20offline.access"
        f"&state={state}"
        f"&code_challenge={challenge}"
        f"&code_challenge_method=S256"
    )


@router.get("/auth/twitter/callback")
async def twitter_callback(code: str, state: str, db: Session = Depends(get_db)):
    
    
    verifier = verifier_store.get(state)
    if not verifier:
        return {"error": "Missing code_verifier for state."}

    basic_auth = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    headers = {
        "Authorization": f"Basic {basic_auth}",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    async with httpx.AsyncClient() as client:
        # 1. Exchange code for access token
        res = await client.post(
            "https://api.twitter.com/2/oauth2/token",
            data={
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri,
                "code_verifier": verifier
            },
            headers=headers,
        )
        token_data = res.json()
        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")

        if not access_token:
            return {"error": "Failed to retrieve access token.", "details": token_data}

        # 2. Get user ID and username
        user_res = await client.get(
            "https://api.twitter.com/2/users/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        user_data = user_res.json()
        twitter_id = user_data.get("data", {}).get("id")
        twitter_username = user_data.get("data", {}).get("username")

        # 3. Get profile image URL
        image_res = await client.get(
            f"https://api.twitter.com/2/users/{twitter_id}?user.fields=profile_image_url",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        image_data = image_res.json()
        profile_image_url = image_data.get("data", {}).get("profile_image_url", "")
        if profile_image_url:
            profile_image_url = profile_image_url.replace("_normal", "")  # High-res image

        # 4. Save or update token
        existing_token = db.query(TwitterToken).filter_by(twitter_id=twitter_id).first()
        if existing_token:
            existing_token.access_token = access_token
            existing_token.refresh_token = refresh_token
            existing_token.updated_at = datetime.utcnow()
        else:
            db.add(TwitterToken(
                twitter_id=twitter_id,
                access_token=access_token,
                refresh_token=refresh_token
            ))
        db.commit()

        # 5. Check if user exists
        existing_user = db.query(User).filter_by(twitter_id=twitter_id).first()
        user_exists = existing_user is not None

        jwt_token = None
        if user_exists:
            existing_user.nft_image_url = profile_image_url  # ✅ Save image to DB
            db.commit()
            jwt_token = create_access_token(data={"sub": str(existing_user.id)})

    # 6. 🔁 Redirect to frontend with info
    query_params = urlencode({
        "access_token": jwt_token or "",
        "username": twitter_username,
        "twitter_id": twitter_id,
        "image": profile_image_url,
        "userExists": str(user_exists).lower()
    })

    return RedirectResponse(f"https://www.glaria.xyz/oauth-success?{query_params}")





@router.get("/api/auth/nonce")
async def get_nonce(address: str, db: Session = Depends(get_db)):
    # ✅ Validate address format
    if not address or not address.startswith("0x") or len(address) != 42:
        raise HTTPException(status_code=400, detail="Invalid wallet address")

    # ✅ Clean the address
    clean_address = address.strip().lower()

      # ✅ Delete any existing nonce for this address
    db.query(WalletNonce).filter_by(address=clean_address).delete()

    # ✅ Generate and store nonce
    nonce = ''.join(random.choices(string.digits, k=6))
    db_nonce = WalletNonce(address=clean_address, nonce=nonce)
    db.add(db_nonce)
    db.commit()

    return {"nonce": nonce}


class WalletLoginWithNonce(BaseModel):
    address: str
    signature: str


class WalletLoginRequest(BaseModel):
    address: str
    signature: str

@router.post("/api/auth/wallet-login")
async def wallet_login(payload: WalletLoginRequest, db: Session = Depends(get_db)):
    address = payload.address.strip().lower()
    signature = payload.signature

    # ✅ Try to get latest nonce (used or unused)
    db_nonce = (
        db.query(WalletNonce)
        .filter(WalletNonce.address == address)
        .order_by(WalletNonce.created_at.desc())
        .first()
    )

    if not db_nonce:
        raise HTTPException(status_code=400, detail="No nonce available for this address")

    # ✅ Reconstruct the original message
    message = f"Sign this nonce to authenticate: {db_nonce.nonce}"
    encoded_msg = encode_defunct(text=message)

    try:
        recovered = Account.recover_message(encoded_msg, signature=signature)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Signature verification failed: {str(e)}")

    # ✅ Compare recovered address
    if recovered.lower() != address:
        raise HTTPException(status_code=401, detail="Invalid signature")

    # ✅ (Optional) Only delete nonce if you want one-time usage
    # db.delete(db_nonce)
    # db.commit()

    # ✅ Return login success
    return {"message": "Authenticated", "address": recovered}