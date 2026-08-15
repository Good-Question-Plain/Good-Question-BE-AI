from pydantic import BaseModel


class SyncProfileRequest(BaseModel):
    name: str


class VerifyPasswordRequest(BaseModel):
    password: str


class MessageResponse(BaseModel):
    message: str
