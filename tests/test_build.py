import json
import re

import pytest

from emrf import build
from emrf.schema import SchemaError


def _write(root, d):
    folder = root / d["bc"] / "extracted"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{d['speech_id']}.json").write_text(json.dumps(d), encoding="utf-8")


def _data(html):
    m = re.search(r'<script id="data" type="application/json">(.*?)</script>', html, re.S)
    return json.loads(m.group(1).replace("<\\/", "</"))


def test_build_smoke(tmp_path, make_record):
    ext, raw = tmp_path / "ext", tmp_path / "raw"
    com = make_record(composite=-0.5)
    ata = make_record(doc_type="ata", date="2026-10-08", composite=0.0)
    for d in (com, ata):
        _write(ext, d)
    (raw / "banxico" / "raw").mkdir(parents=True)
    (raw / "banxico" / "raw" / f"{com['speech_id']}.md").write_text("texto </script> cru", encoding="utf-8")
    (raw / "banxico" / "raw" / f"{ata['speech_id']}.md").write_text("texto da ata", encoding="utf-8")
    out = build.build(today="2026-10-20", out=tmp_path / "index.html",
                      extracted_root=ext, raw_root=raw)
    html = out.read_text(encoding="utf-8")
    data = _data(html)
    assert list(data["bcs"]) == ["banxico"]            # só BC com dados vira aba
    bx = data["bcs"]["banxico"]
    assert {d["speech_id"] for d in bx["docs"]} == {com["speech_id"], ata["speech_id"]}
    assert [p["level"] for p in bx["series"]] == [-0.5, 0.0]
    assert "texto </script> cru" in [d["text"] for d in bx["docs"] if d["speech_id"] == com["speech_id"]][0]
    assert bx["kpis"]["board_level"] == ata["llm_scores"]["composite_hawk_dove"] == 0.0


def test_build_rejects_member_outside_roster(tmp_path, make_record):
    ext = tmp_path / "ext"
    _write(ext, make_record())
    _write(ext, make_record(track="membro", doc_type="call_privado",
                            member_id="fulano", date="2026-09-30"))
    with pytest.raises(SchemaError, match="fulano"):
        build.build(today="2026-10-20", out=tmp_path / "i.html",
                    extracted_root=ext, raw_root=tmp_path)


def test_build_fails_on_missing_raw(tmp_path, make_record):
    ext = tmp_path / "ext"
    rec = make_record()
    _write(ext, rec)
    with pytest.raises(SchemaError, match=rec["speech_id"]):
        build.build(today="2026-10-20", out=tmp_path / "i.html",
                    extracted_root=ext, raw_root=tmp_path)
