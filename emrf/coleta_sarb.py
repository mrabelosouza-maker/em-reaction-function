"""Funções puras da coleta do SARB (a rede fica no script).

Só statements do MPC: o SARB não publica ata. Data da reunião = data de publicação do statement.
"""
from __future__ import annotations

import json
import re
from datetime import datetime

BASE = "https://www.resbank.co.za"
LISTA = (BASE + "/bin/sarb/solr/searchForPublication?operator=OR"
         "&tagsListAuthored=SARB:Publications/statements/monetary-policy-statements"
         "&childTagSelected=&parentTag=&rows=40&start=0&year=&sort=publishDate_desc&yearList=false")
TITULO = "Statement of the Monetary Policy Committee"
_PDF = re.compile(r'href="([^"]+\.pdf)"', re.I)


def parse_lista(text: str) -> tuple[list[dict], list[str]]:
    """Statements da busca do site; devolve (linhas, problemas) - nada é descartado em silêncio."""
    out, problemas = [], []
    for x in json.loads(text).get("solrDocumentList", []):
        if not x.get("title", "").startswith(TITULO):
            continue
        try:
            # "Sep 23, 2026, 5:00:00 PM": só dia e ano interessam
            date = datetime.strptime(", ".join(x["publishDate"].split(", ")[:2]), "%b %d, %Y").date().isoformat()
        except (KeyError, IndexError, ValueError):
            problemas.append(f"'{x.get('title')}': publishDate ilegível {x.get('publishDate')!r}")
            continue
        out.append({"date": date, "meeting_date": date, "url": BASE + x["url"]})
    return out, problemas


def statement_pdf(html: str) -> str | None:
    """O PDF do statement na página de detalhe (o outro é o forecast); None se não houver exatamente um."""
    pdfs = sorted({h for h in _PDF.findall(html) if "statement" in h.rsplit("/", 1)[-1].lower()})
    if len(pdfs) != 1:
        return None
    return pdfs[0] if pdfs[0].startswith("http") else BASE + pdfs[0]
