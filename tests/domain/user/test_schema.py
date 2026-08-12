import uuid
import pytest
from app.models.child import Child


def test_child_update_request_all_fields_optional():
    from app.domain.user.schema import ChildUpdateRequest

    req = ChildUpdateRequest()
    assert req.name is None
    assert req.birth_year is None


def test_child_update_request_partial_fields():
    from app.domain.user.schema import ChildUpdateRequest

    req = ChildUpdateRequest(name="지오")
    assert req.name == "지오"
    assert req.birth_year is None


def test_child_response_from_orm_model():
    from app.domain.user.schema import ChildResponse

    child_id = uuid.uuid4()
    parent_id = uuid.uuid4()
    child = Child(id=child_id, parent_id=parent_id, name="지오", birth_year=2018)
    resp = ChildResponse.model_validate(child)

    assert resp.id == child_id
    assert resp.name == "지오"
    assert resp.birth_year == 2018


def test_parent_response_fields():
    from app.domain.user.schema import ParentResponse

    parent_id = uuid.uuid4()
    resp = ParentResponse(id=parent_id, name="홍길동", email="test@example.com")

    assert resp.id == parent_id
    assert resp.name == "홍길동"
    assert resp.email == "test@example.com"
