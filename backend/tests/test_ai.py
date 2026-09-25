from types import SimpleNamespace

import anthropic
import httpx
import pytest

from app.core.config import get_settings
from app.services import ai


class FakeClient:
    def __init__(self, result=None, exc=None):
        self.result, self.exc, self.calls = result, exc, []
        self.messages = self

    def parse(self, **kwargs):
        self.calls.append(kwargs)
        if self.exc:
            raise self.exc
        return self.result


@pytest.fixture
def fake(monkeypatch):
    monkeypatch.setenv("AI_ENABLED", "true")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    get_settings.cache_clear()

    def install(**kw):
        client = FakeClient(**kw)
        monkeypatch.setattr(ai, "_client", lambda: client)
        return client

    return install


def test_ai_disabled_without_key():
    with pytest.raises(ai.AIError):
        ai._client()


def test_classify_uses_structured_output_and_filters_unrequested(fake):
    batch = ai.ClassificationBatch(items=[
        ai.IngredientClassification(input_name="yacon syrup", canonical_name="yacon syrup",
                                    categories=["added_sugar"], rationale="syrup"),
        ai.IngredientClassification(input_name="hallucinated", canonical_name="x", categories=["preservative"], rationale=""),
    ])
    client = fake(result=SimpleNamespace(stop_reason="end_turn", parsed_output=batch))
    out = ai.classify(["yacon syrup"])
    assert list(out) == ["yacon syrup"]
    call = client.calls[0]
    assert call["output_format"] is ai.ClassificationBatch
    assert call["model"] == get_settings().ai_model


def test_refusal_is_treated_as_failure(fake):
    fake(result=SimpleNamespace(stop_reason="refusal", parsed_output=None))
    with pytest.raises(ai.AIError):
        ai.classify(["x"])


def test_network_errors_become_ai_errors(fake):
    fake(exc=anthropic.APIConnectionError(request=httpx.Request("POST", "https://api.anthropic.com")))
    with pytest.raises(ai.AIError):
        ai.extract_label(b"img", "image/png", "ocr")


def test_explanation_prompt_states_score_is_final(fake):
    client = fake(result=SimpleNamespace(stop_reason="end_turn", parsed_output=ai.Explanation(summary="Fine.")))
    assert ai.explain("Bar", 55, "YELLOW", [{"label": "Added sugar", "points": -25, "detail": "d"}], ["sugar"], []) == "Fine."
    assert "do not change or recompute it" in client.calls[0]["messages"][0]["content"]
