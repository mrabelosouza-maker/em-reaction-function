"""Coleta os statements do MPC do SARB (resbank.co.za) desde START_DATE.

Idempotente: nunca reescreve um raw existente. Documento sem texto legível é
reportado com ERRO e não é gravado (nunca descartado em silêncio).
O WAF do site rejeita requisição sem cabeçalhos de navegador (UA e Accept-Language).
"""
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import fitz  # noqa: E402  (pymupdf)

from emrf import config  # noqa: E402
from emrf.coleta_banxico import pendentes, raw_header  # noqa: E402
from emrf.coleta_sarb import LISTA, parse_lista, statement_pdf  # noqa: E402
from emrf.schema import colegiado_id  # noqa: E402

BC = "sarb"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                         "(KHTML, like Gecko) Chrome/126.0 Safari/537.36",
           "Accept-Language": "en-US,en;q=0.9",
           "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8"}
MIN_CHARS = 1000
FALHAS: list[str] = []


def _falha(msg: str) -> None:
    print(msg)
    FALHAS.append(msg)


def _get(url: str, tentativas: int = 3) -> bytes:
    """O WAF derruba conexões de forma intermitente (WinError 10054); a mesma requisição passa depois."""
    for i in range(tentativas):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=60).read()
        except OSError:
            if i == tentativas - 1:
                raise
            time.sleep(5 * (i + 1))


def statements() -> None:
    try:
        rows, problemas = parse_lista(_get(LISTA).decode("utf-8"))
    except Exception as exc:
        _falha(f"ERRO listagem de statements: {exc}")
        return
    if not rows:
        _falha("ERRO nenhum statement reconhecido na listagem (formato mudou?)")
    for pb in problemas:
        _falha(f"ERRO statement: {pb}")
    for s in sorted(rows, key=lambda s: s["date"]):
        if s["date"] < config.START_DATE:
            continue
        dest = config.raw_dir(BC) / f"{colegiado_id('comunicado', s['date'], s['meeting_date'])}.md"
        if dest.exists():
            continue
        try:
            pdf = statement_pdf(_get(s["url"]).decode("utf-8", errors="replace"))
            if pdf is None:
                _falha(f"ERRO statement {s['date']}: PDF do statement ausente ou ambíguo em {s['url']}")
                continue
            with fitz.open(stream=_get(pdf), filetype="pdf") as doc:
                text = chr(10).join(page.get_text() for page in doc)
        except Exception as exc:
            _falha(f"ERRO statement {s['date']} {s['url']}: {exc}")
            continue
        if len(text.strip()) < MIN_CHARS:
            _falha(f"ERRO texto ilegível ou curto ({len(text.strip())} chars): statement {s['date']} {pdf}")
            continue
        dest.write_text(raw_header("comunicado", s["date"], s["meeting_date"], pdf, bc=BC)
                        + "\n" + text.strip() + "\n", encoding="utf-8")
        print(f"novo {dest.name} (statement {s['date']})")


if __name__ == "__main__":
    config.raw_dir(BC).mkdir(parents=True, exist_ok=True)
    config.extracted_dir(BC).mkdir(parents=True, exist_ok=True)
    statements()
    for p in pendentes(config.raw_dir(BC), config.extracted_dir(BC)):
        print(f"PENDENTE {p.name}")
    sys.exit(1 if FALHAS else 0)
