"""Coleta comunicados (do _historico local) e minutas (banxico.org.mx) desde START_DATE.

Idempotente: nunca reescreve um raw existente. Documento sem texto legível é
reportado com ERRO e não é gravado (nunca descartado em silêncio).
"""
import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import fitz  # noqa: E402  (pymupdf)

from emrf import config  # noqa: E402
from emrf.coleta_banxico import parse_minutas, pendentes, raw_header  # noqa: E402
from emrf.schema import colegiado_id  # noqa: E402

HIST = Path(r"R:\Macro EMs\Mexico\4. Política Monetária\Comunicados\_historico")
MINUTAS = ("https://www.banxico.org.mx/publicaciones-y-prensa/"
           "minutas-de-las-decisiones-de-politica-monetaria/minutas-politica-monetaria-ta.html")
UA = {"User-Agent": "Mozilla/5.0"}
MIN_CHARS = 1000
FALHAS: list[str] = []


def _falha(msg: str) -> None:
    print(msg)
    FALHAS.append(msg)


def _get(url: str) -> bytes:
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read()


def _write(doc_type, date, meeting_date, url, text) -> None:
    dest = config.raw_dir("banxico") / f"{colegiado_id(doc_type, date, meeting_date)}.md"
    if dest.exists():
        return
    if len(text.strip()) < MIN_CHARS:
        _falha(f"ERRO texto ilegível ou curto ({len(text.strip())} chars): {doc_type} {meeting_date} {url}")
        return
    dest.write_text(raw_header(doc_type, date, meeting_date, url) + "\n" + text.strip() + "\n", encoding="utf-8")
    print(f"novo {dest.name} ({doc_type} {meeting_date})")


def comunicados() -> None:
    index = json.loads((HIST / "_index.json").read_text(encoding="utf-8"))
    for e in sorted(index, key=lambda e: e["fecha"]):
        if e["fecha"] < config.START_DATE:
            continue
        txt = HIST / f"{e['fecha']}.txt"
        if not txt.exists():
            dest = config.raw_dir("banxico") / f"{colegiado_id('comunicado', e['fecha'], e['fecha'])}.md"
            if not dest.exists():
                _falha(f"ERRO comunicado {e['fecha']}: arquivo ausente {txt}")
            continue
        _write("comunicado", e["fecha"], e["fecha"], e["url"], txt.read_text(encoding="utf-8"))


def minutas() -> None:
    try:
        rows, problemas = parse_minutas(_get(MINUTAS).decode("latin-1"))
    except Exception as exc:
        _falha(f"ERRO listagem de minutas: {exc}")
        return
    if not rows:
        _falha("ERRO nenhuma minuta reconhecida na listagem (formato mudou?)")
    for pb in problemas:
        _falha(f"ERRO minuta: {pb}")
    for m in rows:
        if m["meeting_date"] < config.START_DATE:
            continue
        if (config.raw_dir("banxico") / f"{colegiado_id('ata', m['date'], m['meeting_date'])}.md").exists():
            continue
        try:
            with fitz.open(stream=_get(m["url"]), filetype="pdf") as doc:
                text = chr(10).join(page.get_text() for page in doc)
        except Exception as exc:
            _falha(f"ERRO ata {m['meeting_date']} {m['url']}: {exc}")
            continue
        _write("ata", m["date"], m["meeting_date"], m["url"], text)


if __name__ == "__main__":
    config.raw_dir("banxico").mkdir(parents=True, exist_ok=True)
    comunicados()
    minutas()
    for p in pendentes(config.raw_dir("banxico"), config.extracted_dir("banxico")):
        print(f"PENDENTE {p.name}")
    sys.exit(1 if FALHAS else 0)
