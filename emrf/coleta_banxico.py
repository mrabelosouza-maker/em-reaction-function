"""Funções puras da coleta do Banxico (a rede fica no script)."""
from __future__ import annotations

import re
from pathlib import Path

from .schema import colegiado_id, colegiado_title

BASE = "https://www.banxico.org.mx"
MESES = {m: i for i, m in enumerate(
    ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
     "septiembre", "octubre", "noviembre", "diciembre"], start=1)}
MESES["setiembre"] = 9
_TR = re.compile(r"<TR\b.*?</TR>", re.S | re.I)
_DATA = re.compile(r"aria-hidden=true>\s*(\d{2})/(\d{2})/(\d{2})", re.I)
_ANUNCIADA = re.compile(r"anunciada el (\d{1,2}) de (\w+) de (\d{4})", re.I)
_PDF = re.compile(r"HREF=\"([^\"]+\.pdf)\"", re.I)
_META = re.compile(r"<!--\s*(\w+):\s*(.*?)\s*-->")


def parse_minutas(html: str) -> tuple[list[dict], list[str]]:
    """Parseia linha a linha; devolve (linhas, problemas) - nada e descartado em silencio."""
    out, problemas = [], []
    for tr in _TR.findall(html):
        dt = _DATA.search(tr)
        if not dt:
            continue
        dd, mm, yy = dt.groups()
        date = f"20{yy}-{mm}-{dd}"
        an, pdf = _ANUNCIADA.search(tr), _PDF.search(tr)
        faltas = []
        if not an:
            faltas.append("'anunciada el D de MES de YYYY' ausente")
        if not pdf:
            faltas.append("link pdf ausente")
        if an and an.group(2).lower() not in MESES:
            faltas.append(f"mes desconhecido '{an.group(2)}'")
        if faltas:
            problemas.append(f"linha publicada em {date}: " + "; ".join(faltas))
            continue
        d, mes, y = an.groups()
        href = pdf.group(1)
        out.append({"date": date,
                    "meeting_date": f"{y}-{MESES[mes.lower()]:02d}-{int(d):02d}",
                    "url": href if href.startswith("http") else BASE + href})
    return out, problemas


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
    """Só raws colegiados (comunicado/ata); raws de membros vivem na mesma pasta."""
    return sorted(p for p in Path(raw_folder).glob("*.md")
                  if read_meta(p).get("doc_type") in ("comunicado", "ata")
                  and not (Path(extracted_folder) / f"{p.stem}.json").exists())
