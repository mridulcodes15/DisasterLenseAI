"""Gemini-backed incident report generation with a deterministic safe fallback."""

import json
import os
from typing import Any, Protocol

from src.core.models import IncidentReport

from .evidence import extract_evidence
from .prompts import build_report_prompt
from .schemas import REPORT_JSON_SCHEMA, validate_report


DEFAULT_MODEL = "gemini-2.5-flash"


class ReportProvider(Protocol):
    def generate(self, prompt: str, schema: dict[str, Any]) -> Any: ...


class GeminiProvider:
    """Thin adapter around the supported Google Gen AI Python SDK."""

    def __init__(self, api_key: str | None = None, model: str = DEFAULT_MODEL):
        key = api_key or os.getenv("GEMINI_API_KEY")
        if not key:
            raise RuntimeError("GEMINI_API_KEY is not configured.")
        try:
            from google import genai
        except ImportError as exc:
            raise RuntimeError("Install the Google Gen AI SDK with: pip install google-genai") from exc
        self._client = genai.Client(api_key=key)
        self._model = model

    def generate(self, prompt: str, schema: dict[str, Any]) -> Any:
        response = self._client.models.generate_content(
            model=self._model,
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "response_schema": schema,
            },
        )
        parsed = getattr(response, "parsed", None)
        if parsed is not None:
            if hasattr(parsed, "model_dump"):
                return parsed.model_dump()
            if hasattr(parsed, "dict"):
                return parsed.dict()
            return parsed
        text = getattr(response, "text", None)
        if not text:
            raise ValueError("Gemini returned no report content.")
        return json.loads(text)


def _fallback(evidence: dict[str, Any]) -> IncidentReport:
    sources = evidence.get("source_catalog", [])
    return IncidentReport(
        summary="Automated narrative report is unavailable; review the structured backend evidence directly.",
        uncertainties=["An AI-generated report could not be produced or validated."],
        sources=list(sources),
        confidence=None,
    )


def generate_incident_report(
    change_result: Any,
    context_result: Any,
    priority_result: Any = None,
    future_impact: Any = None,
    routing_result: Any = None,
    *,
    provider: ReportProvider | None = None,
    api_key: str | None = None,
    model: str = DEFAULT_MODEL,
) -> IncidentReport:
    """Generate a validated report; return a safe fallback for provider/response failures.

    Pass a provider implementing ``generate(prompt, schema)`` to test or substitute
    the model transport. Production credentials are read from GEMINI_API_KEY.
    """
    evidence = extract_evidence(
        change_result, context_result, priority_result, future_impact, routing_result
    )
    try:
        active_provider = provider or GeminiProvider(api_key=api_key, model=model)
        report = validate_report(
            active_provider.generate(build_report_prompt(evidence), REPORT_JSON_SCHEMA)
        )
        # Backend provenance is authoritative; retain it even if the model omits it.
        report.sources = list(dict.fromkeys(evidence["source_catalog"] + report.sources))
        return report
    except Exception:
        # Do not expose credentials, transport payloads, or provider internals to callers.
        return _fallback(evidence)
