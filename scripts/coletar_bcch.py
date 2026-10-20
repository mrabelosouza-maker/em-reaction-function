"""Coleta comunicados e minutas do BCCh desde START_DATE, a partir do corpus do Vault.

O Vault (`Vault/raw/CL`) é alimentado pelo projeto Modelagem/bc_comunicacao; se um documento
novo não aparecer, rode primeiro o coletor de lá. Idempotente: nunca reescreve um raw existente.
Documento sem data de publicação ou sem texto legível é reportado com ERRO (nunca em silêncio).
"""
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import fitz  # noqa: E402  (pymupdf)

from emrf import config  # noqa: E402
from emrf.coleta_banxico import pendentes, raw_header  # noqa: E402
from emrf.coleta_bcch import HOME, data_da_url, data_do_pdf, parse_vault  # noqa: E402
from emrf.schema import colegiado_id  # noqa: E402

BC = "bcch"
VAULT = Path(r"R:\Macro EMs\Vault\raw\CL")
CLASSES = {"comunicado": ("comunicados", "comunicado"), "minuta": ("minutas", "ata")}
MIN_CHARS = 1000
FALHAS: list[str] = []


def _falha(msg: str) -> None:
    print(msg)
    FALHAS.append(msg)


def _publicacao(classe: str, meta: dict) -> str | None:
    if classe == "comunicado":
        return meta["data"]  # sai no dia da reunião, à noite
    d = data_da_url(meta.get("fonte_url"))
    arq = meta.get("fonte_arquivo")
    if d is None and arq and Path(arq).exists():
        with fitz.open(arq) as doc:
            d = data_do_pdf(doc.metadata.get("creationDate"))
    return d


def coletar() -> None:
    reunioes = set()
    for classe, (pasta, doc_type) in CLASSES.items():
        for src in sorted((VAULT / pasta).glob(f"*-{classe}.md")):
            meta, corpo = parse_vault(src.read_text(encoding="utf-8"))
            meeting = meta.get("data", "")
            if meeting < config.START_DATE:
                continue
            if classe == "comunicado":
                reunioes.add(meeting)
            pub = _publicacao(classe, meta)
            if pub is None:
                _falha(f"ERRO {src.name}: sem data de publicação (nem t= na URL nem PDF em fonte_arquivo)")
                continue
            dest = config.raw_dir(BC) / f"{colegiado_id(doc_type, pub, meeting)}.md"
            if dest.exists():
                continue
            if len(corpo) < MIN_CHARS:
                _falha(f"ERRO texto curto ({len(corpo)} chars): {src}")
                continue
            url = meta.get("fonte_url") or HOME  # sem URL, a home do banco (nunca inventar caminho)
            dest.write_text(raw_header(doc_type, pub, meeting, url, bc=BC) + "\n" + corpo + "\n", encoding="utf-8")
            print(f"novo {dest.name} ({doc_type} {meeting}, publicado {pub})")
    minutas = {parse_vault(p.read_text(encoding="utf-8"))[0].get("data") for p in (VAULT / "minutas").glob("*.md")}
    prazo = (date.today() - timedelta(days=21)).isoformat()
    for r in sorted(reunioes - minutas):
        if r < prazo:
            _falha(f"ERRO minuta da reunião {r} ausente no Vault (rode o coletor do bc_comunicacao)")
        else:
            print(f"AVISO minuta da reunião {r} ainda não está no Vault")


if __name__ == "__main__":
    config.raw_dir(BC).mkdir(parents=True, exist_ok=True)
    config.extracted_dir(BC).mkdir(parents=True, exist_ok=True)
    coletar()
    for p in pendentes(config.raw_dir(BC), config.extracted_dir(BC)):
        print(f"PENDENTE {p.name}")
    sys.exit(1 if FALHAS else 0)
