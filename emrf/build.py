"""Lê os JSON de cada BC, monta o payload e escreve o HTML único."""
from __future__ import annotations

import dataclasses
import json
import re
import shutil
from datetime import date
from pathlib import Path

from . import board, config, html
from .schema import SchemaError, load_records


def load_roster(bc: str) -> list[dict]:
    p = config.REGISTRY / bc / "roster.json"
    return json.loads(p.read_text(encoding="utf-8"))["members"] if p.exists() else []


def _corpo(text: str) -> str:
    """Texto do raw sem o cabeçalho técnico (título '# ...' e linhas '<!-- chave: valor -->')."""
    linhas = text.splitlines()
    i = 0
    while i < len(linhas) and (not linhas[i].strip() or linhas[i].startswith("# ")
                               or re.fullmatch(r"\s*<!--.*-->\s*", linhas[i])):
        i += 1
    return "\n".join(linhas[i:])


def _lvl(v: float) -> str:
    s = f"{abs(v):.1f}".replace(".", ",")
    return s if v == 0 else ("+" if v > 0 else "−") + s


def _pct(v: float) -> str:
    return f"{v:.2f}".replace(".", ",") + "%"


def headline(label: str, series: list[dict], rates: list[dict]) -> str:
    """Título do gráfico principal (padrão pedido pelo analista)."""
    text = f"{label}: evolução da classificação hawk-dove"
    if series and rates:
        text += " e da taxa de juros"
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
        d["text"] = _corpo(raw.read_text(encoding="utf-8"))
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
