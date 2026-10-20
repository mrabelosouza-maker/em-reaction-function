from emrf import coleta_bcch as cc

MD = """---
tipo: fonte
classe: minuta
data: 2026-07-28
voz: colegiado
fonte_url: https://www.bcentral.cl/documents/33528/8545911/Minuta+RPM+Julio+2026.pdf/f07?version=1.0&t=1785884464071
---
REUNIÓN DE POLÍTICA MONETARIA JULIO 2026

texto
"""


def test_parse_vault_separa_frontmatter_e_corpo():
    meta, corpo = cc.parse_vault(MD)
    assert meta["classe"] == "minuta" and meta["data"] == "2026-07-28"
    assert corpo.startswith("REUNIÓN DE POLÍTICA MONETARIA") and "---" not in corpo


def test_parse_vault_sem_frontmatter():
    assert cc.parse_vault("só texto") == ({}, "só texto")


def test_data_da_url_pelo_timestamp():
    assert cc.data_da_url("https://x/a.pdf?version=1.0&t=1785884464071") == "2026-08-04"
    assert cc.data_da_url("https://x/a.pdf") is None
    assert cc.data_da_url(None) is None


def test_data_do_pdf_pela_criacao():
    assert cc.data_do_pdf("D:20260331173503-03'00'") == "2026-03-31"
    assert cc.data_do_pdf("") is None
    assert cc.data_do_pdf(None) is None
