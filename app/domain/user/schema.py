import uuid

from pydantic import BaseModel, ConfigDict


class ParentResponse(BaseModel):
    id: uuid.UUID
    name: str
    email: str


class ChildResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    birth_year: int


class ChildCreateRequest(BaseModel):
    name: str
    birth_year: int


class ChildUpdateRequest(BaseModel):
    name: str | None = None
    birth_year: int | None = None
