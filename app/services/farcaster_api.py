import requests
from app.core.config import settings

FARCASTER_API_KEY = settings.FARCASTER_API_KEY

HEADERS = {
    "Authorization": f"Bearer {FARCASTER_API_KEY}",
    "Accept": "application/json",
}


def extract_cast_hash(url: str) -> str:
    # Example: https://warpcast.com/username/0xabc123
    return url.rstrip("/").split("/")[-1]


def extract_username_from_url(url: str) -> str:
    # Example: https://warpcast.com/username
    return url.rstrip("/").split("/")[-1]


def has_liked_cast(fid: int, target_url: str) -> bool:
    cast_hash = extract_cast_hash(target_url)
    url = f"https://api.farcaster.xyz/v2/cast-likes/{cast_hash}"
    response = requests.get(url, headers=HEADERS)

    if response.status_code == 200:
        likes = response.json().get("likes", [])
        return any(like.get("fid") == fid for like in likes)

    print(f"[has_liked_cast] Failed to fetch likes: {response.status_code}")
    return False


def has_recasted_cast(fid: int, target_url: str) -> bool:
    cast_hash = extract_cast_hash(target_url)
    url = f"https://api.farcaster.xyz/v2/cast-recasts/{cast_hash}"
    response = requests.get(url, headers=HEADERS)

    if response.status_code == 200:
        recasts = response.json().get("recasts", [])
        return any(recast.get("fid") == fid for recast in recasts)

    print(f"[has_recasted_cast] Failed to fetch recasts: {response.status_code}")
    return False


def has_replied_to_cast(fid: int, target_url: str) -> bool:
    cast_hash = extract_cast_hash(target_url)
    url = f"https://api.farcaster.xyz/v2/cast-replies/{cast_hash}"
    response = requests.get(url, headers=HEADERS)

    if response.status_code == 200:
        replies = response.json().get("replies", [])
        return any(reply.get("fid") == fid for reply in replies)

    print(f"[has_replied_to_cast] Failed to fetch replies: {response.status_code}")
    return False


def has_followed_user(fid: int, target_url: str) -> bool:
    target_username = extract_username_from_url(target_url)
    url = f"https://api.farcaster.xyz/v2/user-follows?fid={fid}"
    response = requests.get(url, headers=HEADERS)

    if response.status_code == 200:
        follows = response.json().get("follows", [])
        return any(user.get("username") == target_username for user in follows)

    print(f"[has_followed_user] Failed to fetch follows: {response.status_code}")
    return False