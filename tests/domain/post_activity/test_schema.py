import uuid

from app.domain.post_activity.schema import (
    ActivityResponse,
    RetellRequest,
    RetellResponse,
    SceneCard,
    SubmitRequest,
    SubmitResponse,
    VocabularyItem,
)


def test_scene_card_accepts_null_image():
    card = SceneCard(scene_id=uuid.uuid4(), title="가벼운 지푸라기집", image_url=None)
    assert card.image_url is None


def test_activity_response_cards_list():
    card = SceneCard(scene_id=uuid.uuid4(), title="튼튼한 벽돌집", image_url=None)
    resp = ActivityResponse(attempt_count=0, is_completed=False, cards=[card])
    assert len(resp.cards) == 1
    assert resp.attempt_count == 0


def test_submit_request_parses_uuid_list():
    ids = [uuid.uuid4(), uuid.uuid4()]
    req = SubmitRequest(submitted_order=ids)
    assert len(req.submitted_order) == 2


def test_submit_response_no_vocabulary_when_wrong():
    resp = SubmitResponse(is_correct=False, attempt_count=1)
    assert resp.vocabulary is None


def test_submit_response_includes_vocabulary_when_correct():
    vocab = [VocabularyItem(word="용감한", definition="두렵거나 힘들어도 맞서는")]
    resp = SubmitResponse(is_correct=True, attempt_count=1, vocabulary=vocab)
    assert resp.vocabulary is not None
    assert resp.vocabulary[0].word == "용감한"


def test_retell_request_text():
    req = RetellRequest(retelling_text="옛날에 아기돼지가...")
    assert req.retelling_text == "옛날에 아기돼지가..."


def test_retell_response_fields():
    resp = RetellResponse(story_title="아기돼지 삼형제", utterance_count=8, new_vocabulary_count=4)
    assert resp.utterance_count == 8
    assert resp.new_vocabulary_count == 4
