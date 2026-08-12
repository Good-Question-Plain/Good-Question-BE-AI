import uuid

from app.models.child import Child


def test_child_response_from_orm_model():
    from app.domain.user.schema import ChildResponse

    child_id = uuid.uuid4()
    parent_id = uuid.uuid4()
    child = Child(id=child_id, parent_id=parent_id, name="지오")
    resp = ChildResponse.model_validate(child)

    assert resp.id == child_id
    assert resp.name == "지오"


def test_parent_response_fields():
    from app.domain.user.schema import ParentResponse

    parent_id = uuid.uuid4()
    resp = ParentResponse(id=parent_id, name="홍길동", email="test@example.com")

    assert resp.id == parent_id
    assert resp.name == "홍길동"
    assert resp.email == "test@example.com"
