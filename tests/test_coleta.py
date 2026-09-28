from emrf import coleta_banxico as cb
from emrf import schema

SNIPPET = """<TR><TD tag="[current].bm:referenceDate" class=bmdateview aria-label="20 de Agosto 2026"><SPAN aria-hidden=true>20/08/26
</span></td>
<TD tag="[current].bm:linkText" class=bmtextview>Minuta de la reuni\xf3n de la Junta de Gobierno del Banco de M\xe9xico, con motivo de la decisi\xf3n de pol\xedtica monetaria anunciada el 6 de agosto de 2026
<br/>
<A HREF="/publicaciones-y-prensa/minutas-de-las-decisiones-de-politica-monetaria/{2C056A20-C01E-9A8C-F4C3-6BB70D49BABF}.pdf" target=_blank><SPAN>Minuta</span></A>
</td></tr>
<TR><TD class=bmdateview><SPAN aria-hidden=true>09/07/26
</span></td>
<TD class=bmtextview>Minuta ... anunciada el 25 de junio de 2026
<br/><A HREF="/publicaciones-y-prensa/minutas-de-las-decisiones-de-politica-monetaria/{AAAAAAAA-0000-0000-0000-000000000000}.pdf"><SPAN>Minuta</span></A>
</td></tr>"""


def test_parse_minutas():
    rows, problemas = cb.parse_minutas(SNIPPET)
    assert problemas == []
    assert rows[0] == {
        "date": "2026-08-20", "meeting_date": "2026-08-06",
        "url": "https://www.banxico.org.mx/publicaciones-y-prensa/minutas-de-las-decisiones-de-politica-monetaria/{2C056A20-C01E-9A8C-F4C3-6BB70D49BABF}.pdf"}
    assert rows[1]["meeting_date"] == "2026-06-25" and rows[1]["date"] == "2026-07-09"


def test_header_roundtrip(tmp_path):
    h = cb.raw_header("ata", "2026-08-20", "2026-08-06", "https://x/y.pdf")
    p = tmp_path / "f.md"
    p.write_text(h + "\ntexto", encoding="utf-8")
    meta = cb.read_meta(p)
    assert meta["speech_id"] == schema.colegiado_id("ata", "2026-08-20", "2026-08-06")
    assert meta["doc_type"] == "ata" and meta["meeting_date"] == "2026-08-06"
    assert meta["url"] == "https://x/y.pdf"


def test_pendentes(tmp_path):
    raw, ext = tmp_path / "raw", tmp_path / "ext"
    raw.mkdir(); ext.mkdir()
    for n in ("a", "b"):
        (raw / f"{n}.md").write_text("x", encoding="utf-8")
    (ext / "a.json").write_text("{}", encoding="utf-8")
    assert [p.name for p in cb.pendentes(raw, ext)] == ["b.md"]


def test_parse_minutas_linha_sem_pdf_nao_pareia_com_a_seguinte():
    ruim = ('<TR><TD><SPAN aria-hidden=true>15/10/26\n</span></td><TD>Minuta ... anunciada el 1 de octubre de 2026\n'
            '</td></tr>\n')
    rows, problemas = cb.parse_minutas(ruim + SNIPPET)
    assert len(problemas) == 1 and "2026-10-15" in problemas[0] and "pdf" in problemas[0]
    assert [r["date"] for r in rows] == ["2026-08-20", "2026-07-09"]
    assert rows[0]["meeting_date"] == "2026-08-06"
    assert "2C056A20" in rows[0]["url"]


def test_parse_minutas_mes_desconhecido():
    html = SNIPPET.replace("agosto de 2026", "foobar de 2026")
    rows, problemas = cb.parse_minutas(html)
    assert len(problemas) == 1 and "2026-08-20" in problemas[0] and "foobar" in problemas[0]
    assert [r["date"] for r in rows] == ["2026-07-09"]


def test_parse_minutas_setiembre_e_vazio():
    html = SNIPPET.replace("6 de agosto de 2026", "6 de Setiembre de 2026")
    rows, problemas = cb.parse_minutas(html)
    assert problemas == [] and rows[0]["meeting_date"] == "2026-09-06"
    assert cb.parse_minutas("") == ([], [])
