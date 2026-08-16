from pydantic import BaseModel


class SyncProfileRequest(BaseModel):
    name: str


class VerifyPasswordRequest(BaseModel):
    password: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class MessageResponse(BaseModel):
    message: str
