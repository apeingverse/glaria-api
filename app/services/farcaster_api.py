import requests
from typing import Optional
from app.core.config import settings

NEYNAR_API_KEY = settings.NEYNAR_API_KEY

NEYNAR_HEADERS = {
    "Accept": "application/json",
    "api_key": NEYNAR_API_KEY,
    "x-api-key": NEYNAR_API_KEY,
}

def extract_cast_hash(url: str) -> str:
    return url.rstrip("/").split("/")[-1]

def extract_username_from_url(url: str) -> str:
    return url.rstrip("/").split("/")[-1]

def get_cast_metadata_from_url(target_url: str) -> Optional[dict]:
    url = "https://api.neynar.com/v2/farcaster/cast"
    params = {
        "identifier": target_url,
        "type": "url"
    }
    response = requests.get(url, headers=NEYNAR_HEADERS, params=params)

    if response.status_code == 200:
        data = response.json().get("cast", {})
        return {
            "target_hash": data.get("hash"),
            "target_fid": data.get("author", {}).get("fid")
        }

    print(f"[get_cast_metadata_from_url] Failed: {response.status_code} - {response.text}")
    return None


def has_liked_cast(fid: int, target_url: str) -> bool:
    meta = get_cast_metadata_from_url(target_url)
    if not meta:
        print("[has_liked_cast] Failed to get cast metadata.")
        return False

    params = {
        "fid": fid,
        "target_fid": meta["target_fid"],
        "target_hash": meta["target_hash"],
        "reaction_type": "Like"
    }

    url = "https://api.neynar.com/v1/reactionById"
    response = requests.get(url, headers={"x-api-key": NEYNAR_API_KEY}, params=params)

    print(f"[has_liked_cast] URL: {url}")
    print(f"[has_liked_cast] Params: {params}")
    print(f"[has_liked_cast] Status: {response.status_code}")
    print(f"[has_liked_cast] Response: {response.text}")

    if response.status_code == 200:
        return True
    elif response.status_code == 404:
        return False
    else:
        return False


def has_recasted_cast(fid: int, target_url: str) -> bool:
    meta = get_cast_metadata_from_url(target_url)
    if not meta:
        return False

    url = "https://api.neynar.com/v1/reactionById"
    params = {
        "fid": fid,
        "target_fid": meta["target_fid"],
        "target_hash": meta["target_hash"],
        "reaction_type": "Recast"
    }
    response = requests.get(url, headers={"x-api-key": NEYNAR_API_KEY}, params=params)

    if response.status_code == 200:
        return True
    elif response.status_code == 404:
        return False
    else:
        print(f"[has_recasted_cast] Error: {response.status_code} - {response.text}")
        return False


def has_replied_to_cast(fid: int, target_url: str) -> bool:
    cast_hash = extract_cast_hash(target_url)
    url = f"https://api.neynar.com/v2/farcaster/cast-replies?cast_hash={cast_hash}"
    response = requests.get(url, headers=NEYNAR_HEADERS)

    if response.status_code == 200:
        replies = response.json().get("replies", [])
        return any(reply.get("fid") == fid for reply in replies)

    print(f"[has_replied_to_cast] Failed to fetch replies: {response.status_code} - {response.text}")
    return False


def has_followed_user(fid: int, target_url: str) -> bool:
    target_username = extract_username_from_url(target_url)
    url = f"https://api.neynar.com/v2/farcaster/user-following?fid={fid}"
    response = requests.get(url, headers=NEYNAR_HEADERS)

    if response.status_code == 200:
        following = response.json().get("users", [])
        return any(user.get("username") == target_username for user in following)

    print(f"[has_followed_user] Failed to fetch follows: {response.status_code} - {response.text}")
    return False