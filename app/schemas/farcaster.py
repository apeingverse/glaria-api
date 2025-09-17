from pydantic import BaseModel
from datetime import datetime

class FarcasterNonceResponse(BaseModel):
    nonce: str
    expires_at: datetime


from pydantic import BaseModel
from typing import Optional

class FarcasterProjectSchema(BaseModel):
    id: int
    name: str
    description: Optional[str]
    image_url: Optional[str]
    created_at: Optional[str]  # if you're returning it

    class Config:
        orm_mode = True


from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ProjectListItem(BaseModel):
    id: int
    name: str
    image_url: Optional[str]

    class Config:
        orm_mode = True


class ProjectOut(BaseModel):
    id: int
    name: str
    description: Optional[str]
    image_url: Optional[str]
    created_at: Optional[datetime]

    class Config:
        orm_mode = True