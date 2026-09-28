"""Contrato JSON entre os agentes (não determinísticos) e o build (determinístico).

Validação estrita: saída ruim de agente tem que falhar aqui, com o nome do arquivo,
e não virar um gráfico errado.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import config

_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
_COLEGIADO_TITLE = {"comunicado": "Comunicado", "ata": "Minuta", "rti": "Informe Trimestral"}
REQUIRED = ("speech_id", "bc", "track", "doc_type", "member_id", "title", "date",
            "summary", "key_quotes", "llm_scores", "drivers")


class SchemaError(ValueError):
    pass


def _require(cond: bool, msg: str) -> None:
    if not cond:
        raise SchemaError(msg)


def slugify(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def speech_id(member_id: str, date: str, title: str) -> str:
    """Mesma fórmula de bc_base.py da skill bc-hawk-dove."""
    h = hashlib.sha1(title.strip().lower().encode("utf-8")).hexdigest()[:6]
    return f"{slugify(member_id)}-{date.replace('-', '')}-{h}"


def colegiado_title(doc_type: str, meeting_date: str) -> str:
    return f"{_COLEGIADO_TITLE[doc_type]} {meeting_date}"


def colegiado_id(doc_type: str, date: str, meeting_date: str) -> str:
    return speech_id(config.BOARD_ID, date, colegiado_title(doc_type, meeting_date))


@dataclass
class Record:
    speech_id: str
    bc: str
    track: str
    doc_type: str
    member_id: str
    title: str
    date: str
    summary: str
    key_quotes: list[dict]
    llm_scores: dict[str, Any]
    drivers: dict[str, Any]
    url: str = ""
    source: str = ""
    non_policy: bool = False
    meeting_date: str | None = None
    decision: dict | None = None
    extractor_model: str = ""
    extracted_at: str = ""
    rubric_version: str = ""

    @property
    def composite(self) -> float | None:
        return self.llm_scores.get("composite_hawk_dove")

    @staticmethod
    def from_json(d: dict) -> "Record":
        missing = [k for k in REQUIRED if k not in d]
        _require(not missing, f"{d.get('speech_id', '?')}: campos ausentes {missing}")
        names = {f.name for f in dataclasses.fields(Record)}
        return Record(**{k: v for k, v in d.items() if k in names})

    def validate(self) -> "Record":
        sid = self.speech_id
        _require(self.bc in config.BCS, f"{sid}: bc {self.bc!r} desconhecido")
        _require(self.track in config.TRACKS, f"{sid}: track {self.track!r} inválida")
        _require(self.doc_type in config.TRACKS[self.track],
                 f"{sid}: doc_type {self.doc_type!r} não pertence à trilha {self.track}")
        _require(_DATE.fullmatch(self.date) is not None, f"{sid}: date {self.date!r}")
        _require(sid == speech_id(self.member_id, self.date, self.title),
                 f"{sid}: id inconsistente com member_id/date/title")
        if self.track == "colegiado":
            _require(self.member_id == config.BOARD_ID, f"{sid}: colegiado exige member_id board")
            _require(bool(self.meeting_date) and _DATE.fullmatch(self.meeting_date) is not None,
                     f"{sid}: meeting_date {self.meeting_date!r}")
            _require(self.meeting_date <= self.date, f"{sid}: meeting_date depois de date")
            _require(isinstance(self.decision, dict) and self.decision.get("action") in config.ACTIONS,
                     f"{sid}: decision inválida {self.decision!r}")
        else:
            _require(self.member_id != config.BOARD_ID, f"{sid}: membro não pode ser board")
        for dim, (lo, hi) in config.DIMENSIONS.items():
            v = self.llm_scores.get(dim)
            ok = v is None or (isinstance(v, (int, float)) and not isinstance(v, bool) and lo <= v <= hi)
            _require(ok, f"{sid}: {dim}={v!r} fora de [{lo},{hi}]")
        bias = self.llm_scores.get("near_term_bias") or {}
        _require(bias.get("direction") in config.DIRECTIONS | {None},
                 f"{sid}: near_term_bias.direction {bias.get('direction')!r}")
        _require(set(self.drivers) == set(config.DRIVER_IDS),
                 f"{sid}: drivers devem ser {config.DRIVER_IDS}")
        for k, v in self.drivers.items():
            _require(v.get("intensity") in (0, 1, 2, 3) and v.get("push") in config.PUSHES,
                     f"{sid}: driver {k} inválido {v!r}")
        return self


def load_records(bc: str, folder: Path | None = None) -> list[Record]:
    folder = Path(folder or config.extracted_dir(bc))
    out = []
    for p in sorted(folder.glob("*.json")):
        try:
            r = Record.from_json(json.loads(p.read_text(encoding="utf-8"))).validate()
        except (SchemaError, TypeError, json.JSONDecodeError) as e:
            raise SchemaError(f"{p.name}: {e}") from e
        _require(r.bc == bc, f"{p.name}: bc {r.bc} != {bc}")
        _require(p.stem == r.speech_id, f"{p.name}: nome difere do speech_id {r.speech_id}")
        out.append(r)
    return sorted(out, key=lambda r: (r.date, config.DOC_ORDER[r.doc_type]))
