"""Unit tests for the extractor layer.

Covers the rules extractor on canned scanner-style transcripts, the enum
clamping in ExtractedReport, the auto-selection fallback, and the Claude
extractor's JSON parsing/mapping (with a stubbed API client — no network).
"""
from extract.base import EVENT_TYPES, ExtractedReport, get_extractor
from extract.rules import RulesExtractor


def test_rules_extracts_protest_with_intersection():
    r = RulesExtractor().extract(
        "Units respond, protest forming at 5th and Main, about 200 people, urgent"
    )
    assert r.actionable is True
    assert r.event_type == "Protest"
    assert r.location_text is not None
    assert "5th" in r.location_text and "Main" in r.location_text
    assert r.personnel_count == "200"
    assert r.is_urgent is True


def test_rules_checkpoint_beats_police_when_both_present():
    r = RulesExtractor().extract(
        "Police setting up a checkpoint on Broadway near the bridge"
    )
    # Checkpoint is more specific than the generic police keywords.
    assert r.event_type == "Checkpoint"
    assert r.actionable is True
    assert r.location_text


def test_rules_non_actionable_without_location():
    r = RulesExtractor().extract("Radio check, how do you copy")
    assert r.actionable is False


def test_rules_event_without_location_is_not_actionable():
    r = RulesExtractor().extract("We have a protest happening somewhere downtown")
    # "downtown" isn't matched by the location patterns -> no pin.
    assert r.event_type == "Protest"
    # actionable requires a concrete location phrase
    assert r.actionable is False


def test_event_type_is_always_in_enum():
    for transcript in [
        "shots fired officer needs assistance at 1st and Oak",
        "national guard convoy moving down Elm Street",
        "suspect in custody at the 1200 block of Pine Street",
        "gibberish kshshsh static",
    ]:
        r = RulesExtractor().extract(transcript)
        assert r.event_type in EVENT_TYPES


def test_normalized_clamps_bad_values():
    r = ExtractedReport(
        actionable=True, event_type="Explosion", confidence_level="Certain"
    ).normalized()
    assert r.event_type == "Other"
    assert r.confidence_level == "Low"


def test_get_extractor_falls_back_to_rules(monkeypatch):
    import config

    monkeypatch.setattr(config, "EXTRACTOR", "auto")
    monkeypatch.setattr(config, "ANTHROPIC_API_KEY", "")
    assert isinstance(get_extractor(), RulesExtractor)


def test_claude_parses_json_and_maps_fields(monkeypatch):
    """Stub the Anthropic client so we test parsing/mapping, not the network."""
    import config

    monkeypatch.setattr(config, "ANTHROPIC_API_KEY", "test-key")

    from extract import claude as claude_mod

    class _Block:
        type = "text"
        text = (
            'Here you go: {"actionable": true, "event_type": "Arrest", '
            '"event_subtype": "traffic stop", "personnel_count": 2, '
            '"vehicle_count": null, "confidence_level": "High", '
            '"is_urgent": false, "location_text": "5th and Main", '
            '"description": "Subject taken into custody."}'
        )

    class _Msg:
        content = [_Block()]

    class _Messages:
        def create(self, **kwargs):
            return _Msg()

    class _FakeClient:
        def __init__(self, *a, **k):
            self.messages = _Messages()

    # Build the extractor without importing the real SDK.
    ext = object.__new__(claude_mod.ClaudeExtractor)
    ext._client = _FakeClient()
    ext._model = "test-model"

    r = ext.extract("someone getting arrested at 5th and main after a stop")
    assert r.actionable is True
    assert r.event_type == "Arrest"
    assert r.event_subtype == "traffic stop"
    assert r.personnel_count == "2"
    assert r.confidence_level == "High"
    assert r.location_text == "5th and Main"


def test_claude_no_location_marks_not_actionable(monkeypatch):
    from extract import claude as claude_mod

    class _Block:
        type = "text"
        text = '{"actionable": true, "event_type": "Police", "location_text": null}'

    class _Msg:
        content = [_Block()]

    class _Messages:
        def create(self, **kwargs):
            return _Msg()

    class _FakeClient:
        def __init__(self, *a, **k):
            self.messages = _Messages()

    ext = object.__new__(claude_mod.ClaudeExtractor)
    ext._client = _FakeClient()
    ext._model = "test-model"

    r = ext.extract("chatter with no place")
    assert r.actionable is False
