import copy

import pytest

from emrf import schema

_BASE = {
    "bc": "banxico",
    "track": "colegiado",
    "doc_type": "comunicado",
    "member_id": "board",
    "date": "2026-09-24",
    "meeting_date": "2026-09-24",
    "url": "https://www.banxico.org.mx/",
    "source": "banxico",
    "non_policy": False,
    "decision": {"action": "hold", "rate": "6.50%", "vote": "5-0", "dissents": []},
    "summary": "The Board held.",
    "key_quotes": [
        {"quote": "a", "context": "c", "dimension": "composite_hawk_dove"},
        {"quote": "b", "context": "c", "dimension": "near_term_bias"},
    ],
    "llm_scores": {
        "composite_hawk_dove": 0.5, "mandate_weight": 1, "inflation_conviction": 3,
        "labor_concern": 2, "policy_stance_read": 3,
        "near_term_bias": {"direction": "hold", "pace": "data-dependent"},
        "theme_flags": [],
    },
    "drivers": {d: {"intensity": 1, "push": "neutral"} for d in
                ["supply_shocks", "underlying_inflation", "fx_external",
                 "labor_market", "growth_demand", "other"]},
    "extractor_model": "test", "extracted_at": "2026-09-28T00:00:00Z",
    "rubric_version": "1.0-generic",
}


def _make(**over) -> dict:
    d = copy.deepcopy(_BASE)
    composite = over.pop("composite", "keep")
    d.update(over)
    if composite != "keep":
        d["llm_scores"]["composite_hawk_dove"] = composite
    if d["track"] == "colegiado" and d["doc_type"] in ("comunicado", "ata", "rti"):
        d["title"] = schema.colegiado_title(d["doc_type"], d["meeting_date"])
    elif d["track"] == "colegiado":
        d["title"] = f"Doc {d['date']}"  # doc_type inválido: o teste espera falha de schema
    else:
        d.setdefault("title", f"Call {d['date']}")
        d.pop("meeting_date", None)
        d.pop("decision", None)
    d["speech_id"] = schema.speech_id(d["member_id"], d["date"], d["title"])
    return d


@pytest.fixture
def make_record():
    return _make
