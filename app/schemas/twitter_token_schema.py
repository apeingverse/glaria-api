from pydantic import BaseModel
from datetime import datetime

class TwitterTokenOut(BaseModel):
    twitter_id: str
    access_token: str
    refresh_token: str | None = None
    updated_at: datetime

    class Config:
        from_attributes = True