import requests
import os

API_KEY = os.getenv("FARCASTER_API_KEY")
HEADERS = {"Authorization": f"Bearer {API_KEY}"}

def has_liked_cast(fid: int, target_url: str) -> bool:
    # TODO: Replace with real call (e.g., Neynar GET /likes?fid=xxx)
    print(f"Checking if fid {fid} liked {target_url}")
    return True  # mock success

def has_recasted_cast(fid: int, target_url: str) -> bool:
    print(f"Checking if fid {fid} recasted {target_url}")
    return True

def has_replied_to_cast(fid: int, target_url: str) -> bool:
    print(f"Checking if fid {fid} replied to {target_url}")
    return True

def has_followed_user(fid: int, target_url: str) -> bool:
    print(f"Checking if fid {fid} followed user at {target_url}")
    return True