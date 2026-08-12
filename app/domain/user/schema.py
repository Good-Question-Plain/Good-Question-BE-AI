import uuid

from pydantic import BaseModel, ConfigDict


class ParentResponse(BaseModel):
    id: uuid.UUID
    name: str
    email: str


class ParentUpdateRequest(BaseModel):
    name: str


class ChildResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    profile_image_url: str | None = None


class ChildCreateRequest(BaseModel):
    name: str
    profile_image_url: str


class PresignedUrlRequest(BaseModel):
    content_type: str


class PresignedUrlResponse(BaseModel):
    upload_url: str
    object_key: str
