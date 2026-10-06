import json

from src.core.models import ChangeResult, ContextResult, IncidentReport
from src.llm.evidence import extract_evidence
from src.llm.schemas import validate_report
from src.llm.service import generate_incident_report


class FakeProvider:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.prompt = None
        self.schema = None

    def generate(self, prompt, schema):
        self.prompt = prompt
        self.schema = schema
        if self.error:
            raise self.error
        return self.result


def valid_report(**updates):
    result = {
        "summary": "Observed change is reported in the supplied analysis.",
        "observations": ["The backend reports 2.5 km2 affected."],
        "priority_zones": [],
        "uncertainties": ["Population estimate coverage is incomplete."],
        "recommendations": ["Verify conditions with local responders."],
        "sources": [],
        "confidence": 0.7,
    }
    result.update(updates)
    return result


def test_extract_evidence_omits_large_geometry_and_mask():
    change = ChangeResult(
        status="complete", disaster_type="flood", change_mask=object(),
        change_geometry=object(), affected_area_km2=2.5, sources=["satellite"],
    )
    evidence = extract_evidence(change, ContextResult(population_exposed=1200))
    assert evidence["change_detection"]["affected_area_km2"] == 2.5
    assert "change_mask" not in evidence["change_detection"]
    assert "change_geometry" not in evidence["change_detection"]
    assert evidence["source_catalog"] == ["satellite"]
    json.dumps(evidence)


def test_generate_report_uses_mock_provider_and_preserves_backend_sources():
    provider = FakeProvider(valid_report())
    report = generate_incident_report(
        ChangeResult(status="complete", disaster_type="flood", sources=["Sentinel-1"]),
        ContextResult(sources=["WorldPop"]),
        provider=provider,
    )
    assert isinstance(report, IncidentReport)
    assert report.summary.startswith("Observed change")
    assert report.sources == ["Sentinel-1", "WorldPop"]
    assert "untrusted data" in provider.prompt
    assert provider.schema["required"]


def test_provider_failure_returns_safe_fallback_with_provenance():
    report = generate_incident_report(
        ChangeResult(status="complete", disaster_type="flood", sources=["catalog"]),
        ContextResult(),
        provider=FakeProvider(error=RuntimeError("secret transport details")),
    )
    assert "unavailable" in report.summary
    assert report.sources == ["catalog"]
    assert report.confidence is None
    assert "secret" not in str(report)


def test_invalid_model_output_returns_fallback():
    report = generate_incident_report(
        ChangeResult(status="complete", disaster_type="flood"),
        ContextResult(),
        provider=FakeProvider({"summary": "missing fields"}),
    )
    assert "unavailable" in report.summary


def test_validator_rejects_out_of_range_confidence():
    try:
        validate_report(valid_report(confidence=1.2))
    except ValueError as exc:
        assert "confidence" in str(exc)
    else:
        raise AssertionError("out-of-range confidence should be rejected")


def test_api_key_missing_returns_fallback_without_sdk_or_network_call(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    report = generate_incident_report(ChangeResult("complete", "flood"), ContextResult())
    assert "unavailable" in report.summary
