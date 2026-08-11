from pydantic import BaseModel


class SyncProfileRequest(BaseModel):
    name: str


class MessageResponse(BaseModel):
    message: str
