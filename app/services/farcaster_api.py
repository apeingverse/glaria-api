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


def get_cast_metadata_from_url(target_url: str, viewer_fid: Optional[int] = None) -> Optional[dict]:
    url = "https://api.neynar.com/v2/farcaster/cast"
    params = {
        "identifier": target_url,
        "type": "url"
    }
    if viewer_fid:
        params["viewer_fid"] = viewer_fid

    response = requests.get(url, headers=NEYNAR_HEADERS, params=params)

    print(f"[get_cast_metadata_from_url] Request URL: {url}")
    print(f"[get_cast_metadata_from_url] Params: {params}")
    print(f"[get_cast_metadata_from_url] Status Code: {response.status_code}")
    print(f"[get_cast_metadata_from_url] Response: {response.text}")

    if response.status_code == 200:
        cast = response.json().get("cast", {})
        return {
            "target_hash": cast.get("hash"),
            "target_fid": cast.get("author", {}).get("fid"),
            "liked": cast.get("viewer_context", {}).get("liked", False),
            "recasted": cast.get("viewer_context", {}).get("recasted", False),
        }

    return None


def has_liked_cast(fid: int, target_url: str) -> bool:
    meta = get_cast_metadata_from_url(target_url, viewer_fid=fid)
    if not meta:
        print("[has_liked_cast] Failed to get cast metadata.")
        return False

    print(f"[has_liked_cast] Meta: {meta}")
    return meta.get("liked", False)


def has_recasted_cast(fid: int, target_url: str) -> bool:
    meta = get_cast_metadata_from_url(target_url, viewer_fid=fid)
    if not meta:
        print("[has_recasted_cast] Failed to get cast metadata.")
        return False

    print(f"[has_recasted_cast] Meta: {meta}")
    return meta.get("recasted", False)


def has_replied_to_cast(fid: int, target_url: str) -> bool:
    cast_hash = extract_cast_hash(target_url)
    url = f"https://api.neynar.com/v2/farcaster/cast-replies?cast_hash={cast_hash}"
    response = requests.get(url, headers=NEYNAR_HEADERS)

    print(f"[has_replied_to_cast] URL: {url}")
    print(f"[has_replied_to_cast] Status Code: {response.status_code}")
    print(f"[has_replied_to_cast] Response: {response.text}")

    if response.status_code == 200:
        replies = response.json().get("replies", [])
        return any(reply.get("fid") == fid for reply in replies)

    return False


def has_followed_user(fid: int, target_url: str) -> bool:
    target_username = extract_username_from_url(target_url)
    url = f"https://api.neynar.com/v2/farcaster/user-following?fid={fid}"
    response = requests.get(url, headers=NEYNAR_HEADERS)

    print(f"[has_followed_user] URL: {url}")
    print(f"[has_followed_user] Status Code: {response.status_code}")
    print(f"[has_followed_user] Response: {response.text}")

    if response.status_code == 200:
        following = response.json().get("users", [])
        return any(user.get("username") == target_username for user in following)

    return False