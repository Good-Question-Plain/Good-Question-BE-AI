import uuid
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, computed_field


class ParentResponse(BaseModel):
    id: uuid.UUID
    name: str
    email: str
    profile_image_url: str | None = None


class ParentUpdateRequest(BaseModel):
    name: str | None = None
    profile_image_url: str | None = None


class ChildResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    profile_image_url: str | None = None
    birth_year: int | None = None

    @computed_field
    @property
    def age(self) -> int | None:
        if self.birth_year is None:
            return None
        return datetime.now(timezone.utc).year - self.birth_year


class ChildCreateRequest(BaseModel):
    name: str
    profile_image_url: str


class ChildUpdateRequest(BaseModel):
    name: str | None = None
    profile_image_url: str | None = None
    birth_year: int | None = None


class PresignedUrlRequest(BaseModel):
    content_type: str
    target: Literal["parent", "child"]


class PresignedUrlResponse(BaseModel):
    upload_url: str
    object_key: str
