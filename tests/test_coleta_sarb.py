import json

from emrf import coleta_banxico as cb
from emrf import coleta_sarb as cs
from emrf import schema

LISTA = json.dumps({"total": 3, "solrDocumentList": [
    {"publishDate": "Sep 23, 2026, 5:00:00 PM", "title": "Statement of the Monetary Policy Committee September 2026",
     "url": "/en/home/publications/publication-detail-pages/statements/monetary-policy-statements/2026/september"},
    {"publishDate": "Jan 25, 2024, 3:11:00 PM", "title": "Appointment of Dr David Fowkes in the Monetary Policy Committee",
     "url": "/en/home/publications/publication-detail-pages/media-releases/2024/x"},
    {"publishDate": "Mar 20, 2025, 4:26:00 PM", "title": "Statement of the Monetary Policy Committee March 2025",
     "url": "/en/home/publications/publication-detail-pages/statements/monetary-policy-statements/2025/march"},
    {"publishDate": "sem data", "title": "Statement of the Monetary Policy Committee May 2099", "url": "/x"},
]})

PAGINA = ('<a href="/content/dam/sarb/publications/statements/monetary-policy-statements/2025/march/'
          'Forecast%20report%20MPC%20March%202025.pdf">Forecast</a>'
          '<a href="/content/dam/sarb/publications/statements/monetary-policy-statements/2025/march/'
          'Statement%20of%20the%20monetary%20policy%20committee%20March%202025%20.pdf">Statement</a>')


def test_parse_lista_so_statements_e_reporta_problemas():
    rows, problemas = cs.parse_lista(LISTA)
    assert [r["meeting_date"] for r in rows] == ["2026-09-23", "2025-03-20"]
    assert rows[0] == {"date": "2026-09-23", "meeting_date": "2026-09-23",
                       "url": "https://www.resbank.co.za/en/home/publications/publication-detail-pages/"
                              "statements/monetary-policy-statements/2026/september"}
    assert len(problemas) == 1 and "sem data" in problemas[0]


def test_statement_pdf_ignora_forecast():
    assert cs.statement_pdf(PAGINA) == (
        "https://www.resbank.co.za/content/dam/sarb/publications/statements/monetary-policy-statements/"
        "2025/march/Statement%20of%20the%20monetary%20policy%20committee%20March%202025%20.pdf")


def test_statement_pdf_ambiguo_ou_ausente():
    assert cs.statement_pdf('<a href="/a/forecast.pdf">') is None
    assert cs.statement_pdf('<a href="/a/x-statement.pdf"><a href="/b/y-statement.pdf">') is None


def test_header_do_sarb():
    h = cb.raw_header("comunicado", "2026-09-23", "2026-09-23", "https://x/y.pdf", bc="sarb")
    assert h.startswith("# SARB — Comunicado 2026-09-23")
    assert "<!-- bc: sarb -->" in h
    assert f"<!-- speech_id: {schema.colegiado_id('comunicado', '2026-09-23', '2026-09-23')} -->" in h
