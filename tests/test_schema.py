import json

import pytest

from emrf import schema
from emrf.schema import Record, SchemaError, load_records


def test_speech_id_matches_skill_formula():
    # mesmo algoritmo de bc_base.py: sha1 do título em minúsculas, 6 hex
    assert schema.speech_id("Heath", "2026-09-24", "X") == "heath-20260924-11f6ad"


def test_colegiado_id_is_deterministic():
    a = schema.colegiado_id("ata", "2026-10-08", "2026-09-24")
    assert a == schema.speech_id("board", "2026-10-08", "Minuta 2026-09-24")


def test_valid_record_passes(make_record):
    r = Record.from_json(make_record()).validate()
    assert r.composite == 0.5


def test_null_composite_allowed(make_record):
    assert Record.from_json(make_record(composite=None)).validate().composite is None


@pytest.mark.parametrize("over, msg", [
    ({"composite": 6}, "fora de"),
    ({"doc_type": "call_privado"}, "não pertence"),
    ({"bc": "fed"}, "bc"),
])
def test_invalid_records_fail(make_record, over, msg):
    d = make_record(**over)
    with pytest.raises(SchemaError, match=msg):
        Record.from_json(d).validate()


def test_colegiado_requires_decision(make_record):
    d = make_record()
    d["decision"] = None
    with pytest.raises(SchemaError, match="decision"):
        Record.from_json(d).validate()


def test_wrong_id_fails(make_record):
    d = make_record()
    d["speech_id"] = "board-20260924-000000"
    with pytest.raises(SchemaError, match="id"):
        Record.from_json(d).validate()


def test_drivers_must_match_rubric(make_record):
    d = make_record()
    del d["drivers"]["other"]
    with pytest.raises(SchemaError, match="drivers"):
        Record.from_json(d).validate()


def test_membro_cannot_be_board(make_record):
    d = make_record(track="membro", doc_type="call_privado", member_id="board")
    with pytest.raises(SchemaError, match="board"):
        Record.from_json(d).validate()


def test_load_records_sorted_and_names_bad_file(tmp_path, make_record):
    ata = make_record(doc_type="ata", date="2026-10-08")
    com = make_record()
    for d in (ata, com):
        (tmp_path / f"{d['speech_id']}.json").write_text(json.dumps(d), encoding="utf-8")
    recs = load_records("banxico", tmp_path)
    assert [r.doc_type for r in recs] == ["comunicado", "ata"]
    bad = make_record(composite=9)
    (tmp_path / f"{bad['speech_id']}x.json").write_text(json.dumps(bad), encoding="utf-8")
    with pytest.raises(SchemaError, match=bad["speech_id"]):
        load_records("banxico", tmp_path)


def test_load_records_catches_malformed_driver(tmp_path, make_record):
    """load_records must catch KeyError from malformed driver and report filename."""
    bad = make_record()
    bad["drivers"]["supply_shocks"] = 1  # Should be dict with intensity and push
    bad_file = tmp_path / f"{bad['speech_id']}.json"
    bad_file.write_text(json.dumps(bad), encoding="utf-8")
    with pytest.raises(SchemaError, match=bad_file.name):
        load_records("banxico", tmp_path)


def test_composite_must_be_integer_or_half(make_record):
    """Composite score must be integer or .5, not 0.37."""
    d = make_record(composite=0.37)
    with pytest.raises(SchemaError, match="inteiro ou .5"):
        Record.from_json(d).validate()


def test_driver_intensity_must_be_int_not_bool(make_record):
    """Driver intensity must be int, not bool (True is rejected)."""
    d = make_record()
    d["drivers"]["supply_shocks"]["intensity"] = True
    with pytest.raises(SchemaError, match="inteiro 0-3"):
        Record.from_json(d).validate()


@pytest.mark.parametrize("kq", ["x", [None], ["a"], [{"quote": ""}], [{"quote": 3}], [{"context": "c"}]])
def test_key_quotes_must_be_list_of_dicts_with_quote(make_record, kq):
    d = make_record()
    d["key_quotes"] = kq
    with pytest.raises(SchemaError, match=d["speech_id"]):
        Record.from_json(d).validate()


def test_near_term_bias_pace_must_be_valid(make_record):
    """near_term_bias.pace must be one of the allowed values."""
    d = make_record()
    d["llm_scores"]["near_term_bias"]["pace"] = "fast"  # Invalid; should be "urgent", "gradual", etc.
    with pytest.raises(SchemaError, match="pace"):
        Record.from_json(d).validate()
