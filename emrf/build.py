"""Lê os JSON de cada BC, monta o payload e escreve o HTML único."""
from __future__ import annotations

import dataclasses
import json
import shutil
from datetime import date
from pathlib import Path

from . import board, config, html
from .schema import SchemaError, load_records


def load_roster(bc: str) -> list[dict]:
    p = config.REGISTRY / bc / "roster.json"
    return json.loads(p.read_text(encoding="utf-8"))["members"] if p.exists() else []


def _lvl(v: float) -> str:
    s = f"{abs(v):.1f}".replace(".", ",")
    return s if v == 0 else ("+" if v > 0 else "−") + s


def _pct(v: float) -> str:
    return f"{v:.2f}".replace(".", ",") + "%"


def headline(label: str, series: list[dict], rates: list[dict]) -> str:
    """Título editorial do gráfico: primeiro e último nível do Board, primeira e última taxa."""
    if not series:
        return label
    a, b = series[0]["level"], series[-1]["level"]
    if a != b:
        junta = f"a Junta saiu de {_lvl(a)} para {_lvl(b)}"
    elif all(p["level"] == a for p in series):
        junta = f"a Junta manteve-se em {_lvl(a)}"
    else:
        junta = f"a Junta voltou ao nível inicial ({_lvl(a)})"
    text = f"{label}: {junta}"
    if rates:
        r0, r1 = rates[0]["rate"], rates[-1]["rate"]
        if r0 == r1:
            text += f" enquanto a taxa ficou em {_pct(r1)}"
        else:
            verbo = "caiu" if r1 < r0 else "subiu"
            text += f" enquanto a taxa {verbo} de {_pct(r0)} para {_pct(r1)}"
    return text


def bc_payload(bc: str, records, roster: list[dict], raw_folder: Path, today: str) -> dict:
    known = {m["member_id"] for m in roster}
    for r in records:
        if r.track == "membro" and r.member_id not in known:
            raise SchemaError(f"{r.speech_id}: member_id {r.member_id} fora de registry/{bc}/roster.json")
    series = board.board_series(records)
    members = [m["member_id"] for m in roster]
    docs = []
    for r in records:
        raw = raw_folder / f"{r.speech_id}.md"
        d = dataclasses.asdict(r)
        if not raw.exists():
            raise SchemaError(f"{r.speech_id}: raw ausente em {raw}")
        d["text"] = raw.read_text(encoding="utf-8")
        docs.append(d)
    rates = board.rate_series(records)
    return {
        **config.BCS[bc],
        "headline": headline(config.BCS[bc]["label"], series, rates),
        "kpis": board.kpis(records, series),
        "series": series,
        "rates": rates,
        "members": roster,
        "points": board.member_points(records, series),
        "heatmap": board.heatmap(records, series, members, today),
        "cards": board.member_cards(records, series, roster),
        "docs": docs,
        "coverage": {"first": min(r.date for r in records), "last": max(r.date for r in records),
                     "n_docs": len(records)},
    }


def build(today: str | None = None, out: Path | None = None,
          extracted_root: Path | None = None, raw_root: Path | None = None) -> Path:
    today = today or date.today().isoformat()
    out = Path(out or config.RESULTS / "index.html")
    extracted_root = Path(extracted_root or config.DATA)
    raw_root = Path(raw_root or config.DATA)
    bcs = {}
    for bc in config.BCS:
        folder = extracted_root / bc / "extracted"
        records = load_records(bc, folder) if folder.exists() else []
        if records:
            bcs[bc] = bc_payload(bc, records, load_roster(bc), raw_root / bc / "raw", today)
    if not bcs:
        raise SchemaError("nenhum BC com documentos classificados")
    out.parent.mkdir(parents=True, exist_ok=True)
    (out.parent / "assets").mkdir(exist_ok=True)
    src, dst = config.ROOT / "assets" / "plotly.min.js", out.parent / "assets" / "plotly.min.js"
    shutil.copyfile(src, dst)
    if dst.stat().st_size != src.stat().st_size:
        raise SchemaError(f"cópia truncada de {dst}")
    text = html.render({"bcs": bcs}, generated=today)
    out.write_text(text, encoding="utf-8", newline="\n")
    want, got = len(text.encode("utf-8")), out.stat().st_size
    if got != want:
        raise SchemaError(f"escrita truncada em {out}: esperado {want} bytes, gravado {got} bytes")
    return out
