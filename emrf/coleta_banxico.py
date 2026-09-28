"""Funções puras da coleta do Banxico (a rede fica no script)."""
from __future__ import annotations

import re
from pathlib import Path

from .schema import colegiado_id, colegiado_title

BASE = "https://www.banxico.org.mx"
MESES = {m: i for i, m in enumerate(
    ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
     "septiembre", "octubre", "noviembre", "diciembre"], start=1)}
_ROW = re.compile(
    r"aria-hidden=true>(\d{2})/(\d{2})/(\d{2}).*?anunciada el (\d{1,2}) de (\w+) de (\d{4}).*?HREF=\"([^\"]+\.pdf)\"",
    re.S | re.I)
_META = re.compile(r"<!--\s*(\w+):\s*(.*?)\s*-->")


def parse_minutas(html: str) -> list[dict]:
    out = []
    for dd, mm, yy, d, mes, y, href in _ROW.findall(html):
        out.append({"date": f"20{yy}-{mm}-{dd}",
                    "meeting_date": f"{y}-{MESES[mes.lower()]:02d}-{int(d):02d}",
                    "url": href if href.startswith("http") else BASE + href})
    return out


def raw_header(doc_type: str, date: str, meeting_date: str, url: str) -> str:
    return (f"# Banxico — {colegiado_title(doc_type, meeting_date)}\n\n"
            f"<!-- speech_id: {colegiado_id(doc_type, date, meeting_date)} -->\n"
            f"<!-- bc: banxico -->\n<!-- doc_type: {doc_type} -->\n"
            f"<!-- date: {date} -->\n<!-- meeting_date: {meeting_date} -->\n"
            f"<!-- url: {url} -->\n")


def read_meta(path: Path) -> dict:
    head = Path(path).read_text(encoding="utf-8")[:2000]
    return dict(_META.findall(head))


def pendentes(raw_folder: Path, extracted_folder: Path) -> list[Path]:
    return sorted(p for p in Path(raw_folder).glob("*.md")
                  if not (Path(extracted_folder) / f"{p.stem}.json").exists())
