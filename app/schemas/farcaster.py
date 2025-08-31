from pydantic import BaseModel
from datetime import datetime

class FarcasterNonceResponse(BaseModel):
    nonce: str
    expires_at: datetime
