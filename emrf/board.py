"""Série do Board (degrau), desvio dos membros, heatmap por ciclo, KPIs e cards.

Nível do Board em t = composto do último documento colegiado com date <= t.
Documento com composto null não move o degrau. Desvio = membro - Board vigente.
"""
from __future__ import annotations

from bisect import bisect_right
from datetime import date as _date, timedelta
from statistics import mean

from .schema import Record


def _avg(xs: list[float]) -> float | None:
    return round(mean(xs), 2) if xs else None


def _day_before(d: str) -> str:
    return (_date.fromisoformat(d) - timedelta(days=1)).isoformat()


def _policy_members(records: list[Record]) -> list[Record]:
    return [r for r in records
            if r.track == "membro" and not r.non_policy and r.composite is not None]


def board_series(records: list[Record]) -> list[dict]:
    return [{"date": r.date, "level": r.composite, "doc_type": r.doc_type,
             "meeting_date": r.meeting_date, "speech_id": r.speech_id}
            for r in records if r.track == "colegiado" and r.composite is not None]


def board_level_at(series: list[dict], date: str) -> float | None:
    i = bisect_right([p["date"] for p in series], date)
    return series[i - 1]["level"] if i else None


def member_points(records: list[Record], series: list[dict]) -> list[dict]:
    out = []
    for r in _policy_members(records):
        b = board_level_at(series, r.date)
        out.append({"date": r.date, "member_id": r.member_id, "doc_type": r.doc_type,
                    "composite": r.composite, "board": b,
                    "deviation": None if b is None else r.composite - b,
                    "speech_id": r.speech_id})
    return out


def meetings(records: list[Record]) -> list[str]:
    return sorted({r.meeting_date for r in records if r.doc_type == "comunicado"})


def heatmap(records: list[Record], series: list[dict], members: list[str], today: str) -> dict:
    ms = meetings(records)
    pts = member_points(records, series)
    board_row: list = []
    level = {m: [] for m in members}
    dev = {m: [] for m in members}
    for k, start in enumerate(ms):
        end = ms[k + 1] if k + 1 < len(ms) else None
        board_row.append(board_level_at(series, _day_before(end) if end else today))
        for mid in members:
            ps = [p for p in pts if p["member_id"] == mid
                  and start <= p["date"] and (end is None or p["date"] < end)]
            level[mid].append(_avg([p["composite"] for p in ps]))
            dev[mid].append(_avg([p["deviation"] for p in ps if p["deviation"] is not None]))
    return {"columns": ms, "board": board_row, "level": level, "deviation": dev}


def kpis(records: list[Record], series: list[dict]) -> dict:
    coms = [r for r in records if r.doc_type == "comunicado"]
    last = coms[-1] if coms else None
    dec = (last.decision or {}) if last else {}
    return {
        "rate": dec.get("rate"), "action": dec.get("action"), "vote": dec.get("vote"),
        "dissents": dec.get("dissents", []),
        "meeting_date": last.meeting_date if last else None,
        "board_level": series[-1]["level"] if series else None,
        "board_delta": series[-1]["level"] - series[-2]["level"] if len(series) > 1 else None,
        "last_doc_type": series[-1]["doc_type"] if series else None,
        "last_doc_date": series[-1]["date"] if series else None,
    }


def member_cards(records: list[Record], series: list[dict], roster: list[dict]) -> list[dict]:
    pol = _policy_members(records)
    cards = []
    for m in roster:
        rs = [r for r in pol if r.member_id == m["member_id"]]
        card = {"member_id": m["member_id"], "name": m["name"], "role": m.get("role", ""),
                "latest": None, "date": None, "doc_type": None, "delta": None,
                "deviation": None, "quote": ""}
        if rs:
            last, prev = rs[-1], (rs[-2] if len(rs) > 1 else None)
            b = board_level_at(series, last.date)
            card.update(latest=last.composite, date=last.date, doc_type=last.doc_type,
                        delta=None if prev is None else last.composite - prev.composite,
                        deviation=None if b is None else last.composite - b,
                        quote=last.key_quotes[0]["quote"] if last.key_quotes else "")
        cards.append(card)
    return cards
