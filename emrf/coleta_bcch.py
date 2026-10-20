"""Funções puras da coleta do BCCh (o disco fica no script).

Fonte: o corpus do Vault (`Vault/raw/CL/{comunicados,minutas}`), mantido pelo projeto
Modelagem/bc_comunicacao. O comunicado sai no dia da reunião; a minuta sai depois, e a data
de publicação vem do timestamp `t=` da URL do bcentral.cl ou, sem URL, da criação do PDF.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone

HOME = "https://www.bcentral.cl"
_FRONT = re.compile(r"\A---\n(.*?)\n---\n?", re.S)
_T = re.compile(r"[?&]t=(\d{13})\b")
_PDF_DATA = re.compile(r"D:(\d{8})")


def parse_vault(text: str) -> tuple[dict, str]:
    """(frontmatter, corpo) de um .md do Vault; sem frontmatter devolve ({}, texto)."""
    text = text.replace("\r\n", "\n")
    m = _FRONT.match(text)
    if not m:
        return {}, text
    meta = dict(ln.split(":", 1) for ln in m.group(1).splitlines() if ":" in ln)
    return {k.strip(): v.strip() for k, v in meta.items()}, text[m.end():].strip()


def data_da_url(url: str | None) -> str | None:
    """Data (UTC) do timestamp em milissegundos `t=` que o bcentral.cl põe na URL do documento."""
    m = _T.search(url or "")
    return datetime.fromtimestamp(int(m.group(1)) / 1000, tz=timezone.utc).date().isoformat() if m else None


def data_do_pdf(creation: str | None) -> str | None:
    """Data do campo creationDate do PDF ("D:20260331173503-03'00'")."""
    m = _PDF_DATA.match(creation or "")
    return f"{m.group(1)[:4]}-{m.group(1)[4:6]}-{m.group(1)[6:]}" if m else None
