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
    return json.loads(m.group(1))


def test_build_smoke(tmp_path, make_record):
    ext, raw = tmp_path / "ext", tmp_path / "raw"
    com = make_record(composite=-0.5)
    ata = make_record(doc_type="ata", date="2026-10-08", composite=0.0)
    for d in (com, ata):
        _write(ext, d)
    (raw / "banxico" / "raw").mkdir(parents=True)
    (raw / "banxico" / "raw" / f"{com['speech_id']}.md").write_text("texto </script> <!-- <script> cru", encoding="utf-8")
    (raw / "banxico" / "raw" / f"{ata['speech_id']}.md").write_text("texto da ata", encoding="utf-8")
    out = build.build(today="2026-10-20", out=tmp_path / "index.html",
                      extracted_root=ext, raw_root=raw)
    html = out.read_text(encoding="utf-8")
    data = _data(html)
    assert list(data["bcs"]) == ["banxico"]            # só BC com dados vira aba
    bx = data["bcs"]["banxico"]
    assert {d["speech_id"] for d in bx["docs"]} == {com["speech_id"], ata["speech_id"]}
    assert [p["level"] for p in bx["series"]] == [-0.5, 0.0]
    assert "texto </script> <!-- <script> cru" in [d["text"] for d in bx["docs"] if d["speech_id"] == com["speech_id"]][0]
    assert bx["kpis"]["board_level"] == ata["llm_scores"]["composite_hawk_dove"] == 0.0
    assert bx["coverage"] == {"first": "2026-09-24", "last": "2026-10-08", "n_docs": 2}
    raw_bytes = out.read_bytes()
    assert b"\r\n" not in raw_bytes
    assert len(raw_bytes) == len(html.encode("utf-8"))
    assert "<!-- <script>" not in html and html.count("<script") == 3  # plotly, data, main
    assert "\\u003c!-- \\u003cscript>" in html
    assert 'src="assets/plotly.min.js"' in html and "cdn.plot.ly" not in html
    assert (tmp_path / "assets" / "plotly.min.js").stat().st_size > 500_000
    assert bx["rates"] == [{"date": "2026-09-24", "rate": 6.5}]
    assert bx["headline"] == "Banxico: a Junta saiu de −0,5 para 0,0 enquanto a taxa ficou em 6,50%"


def test_build_raises_on_short_write(tmp_path, make_record, monkeypatch):
    ext = tmp_path / "ext"
    rec = make_record()
    _write(ext, rec)
    (tmp_path / "banxico" / "raw").mkdir(parents=True)
    (tmp_path / "banxico" / "raw" / f"{rec['speech_id']}.md").write_text("x", encoding="utf-8")
    real = build.Path.write_text
    monkeypatch.setattr(build.Path, "write_text",
                        lambda self, text, **kw: real(self, text[:-10], **kw))
    with pytest.raises(SchemaError, match="bytes"):
        build.build(today="2026-10-20", out=tmp_path / "i.html",
                    extracted_root=ext, raw_root=tmp_path)


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


def _s(*levels):
    return [{"date": f"2026-0{i + 1}-01", "level": v} for i, v in enumerate(levels)]


def _r(*rates):
    return [{"date": f"2026-0{i + 1}-01", "rate": v} for i, v in enumerate(rates)]


def test_headline_moved_and_rate_cut():
    assert build.headline("Banxico", _s(-3.0, -1.5, 0.0), _r(9.5, 8.0, 6.5)) == (
        "Banxico: a Junta saiu de \u22123,0 para 0,0 enquanto a taxa caiu de 9,50% para 6,50%")


def test_headline_hawkish_move_and_hike():
    assert build.headline("SARB", _s(0.5, 2.0), _r(7.25, 7.5)) == (
        "SARB: a Junta saiu de +0,5 para +2,0 enquanto a taxa subiu de 7,25% para 7,50%")


def test_headline_same_ends():
    assert build.headline("Banxico", _s(0.5, 0.5), _r(6.5, 6.5)) == (
        "Banxico: a Junta manteve-se em +0,5 enquanto a taxa ficou em 6,50%")
    assert build.headline("Banxico", _s(-1.0, 0.5, -1.0), _r(7.0, 6.5)) == (
        "Banxico: a Junta voltou ao nível inicial (\u22121,0) enquanto a taxa caiu de 7,00% para 6,50%")


def test_headline_without_rate():
    assert build.headline("BCCh", _s(-2.0, -0.5), []) == "BCCh: a Junta saiu de \u22122,0 para \u22120,5"
    assert build.headline("BCCh", [], []) == "BCCh"


def test_corpo_remove_cabecalho_tecnico():
    raw = "# Banxico — Minuta 2026-06-25\n\n<!-- speech_id: x -->\n<!-- url: y -->\n\nMinuta número 125\n<!-- no meio fica -->\n"
    assert build._corpo(raw) == "Minuta número 125\n<!-- no meio fica -->"
