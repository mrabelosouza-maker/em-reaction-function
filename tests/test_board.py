from emrf import board
from emrf.schema import Record


def recs(make_record, *dicts):
    return sorted((Record.from_json(make_record(**d)).validate() for d in dicts),
                  key=lambda r: (r.date, r.doc_type != "comunicado"))


def base(make_record):
    return recs(make_record,
        {"date": "2026-08-06", "meeting_date": "2026-08-06", "composite": -1.0},
        {"doc_type": "ata", "date": "2026-08-20", "meeting_date": "2026-08-06", "composite": 0.0},
        {"date": "2026-09-24", "meeting_date": "2026-09-24", "composite": 0.5,
         "decision": {"action": "hold", "rate": "6.50%", "vote": "4-1", "dissents": ["Heath (hike)"]}},
        {"doc_type": "ata", "date": "2026-10-08", "meeting_date": "2026-09-24", "composite": None},
        {"track": "membro", "doc_type": "call_privado", "member_id": "heath",
         "date": "2026-09-01", "composite": 2.0},
        {"track": "membro", "doc_type": "fala_publica", "member_id": "heath",
         "date": "2026-09-10", "composite": 1.0},
        {"track": "membro", "doc_type": "fala_publica", "member_id": "heath",
         "date": "2026-09-30", "composite": 1.5},
    )


def test_series_is_step_and_null_does_not_move(make_record):
    s = board.board_series(base(make_record))
    assert [p["level"] for p in s] == [-1.0, 0.0, 0.5]
    assert board.board_level_at(s, "2026-08-05") is None
    assert board.board_level_at(s, "2026-08-20") == 0.0
    assert board.board_level_at(s, "2026-10-20") == 0.5


def test_member_deviation_uses_board_in_force(make_record):
    rs = base(make_record)
    s = board.board_series(rs)
    pts = board.member_points(rs, s)
    assert [(p["date"], p["deviation"]) for p in pts] == [
        ("2026-09-01", 2.0), ("2026-09-10", 1.0), ("2026-09-30", 1.0)]


def test_heatmap_cycles(make_record):
    rs = base(make_record)
    s = board.board_series(rs)
    h = board.heatmap(rs, s, ["heath", "borja"], today="2026-10-20")
    assert h["columns"] == ["2026-08-06", "2026-09-24"]
    assert h["board"] == [0.0, 0.5]          # fim do ciclo, já com a ata
    assert h["level"]["heath"] == [1.5, 1.5]  # média de 2.0 e 1.0; depois só 1.5
    assert h["deviation"]["heath"] == [1.5, 1.0]
    assert h["level"]["borja"] == [None, None]


def test_kpis(make_record):
    rs = base(make_record)
    k = board.kpis(rs, board.board_series(rs))
    assert k["rate"] == "6.50%" and k["action"] == "hold" and k["vote"] == "4-1"
    assert k["board_level"] == 0.5 and k["board_delta"] == 0.5
    assert k["last_doc_type"] == "comunicado"


def test_member_cards(make_record):
    rs = base(make_record)
    roster = [{"member_id": "heath", "name": "Jonathan Heath", "role": "Subgobernador"},
              {"member_id": "borja", "name": "Galia Borja", "role": "Subgobernadora"}]
    cards = {c["member_id"]: c for c in board.member_cards(rs, board.board_series(rs), roster)}
    assert cards["heath"]["latest"] == 1.5 and cards["heath"]["delta"] == 0.5
    assert cards["heath"]["deviation"] == 1.0
    assert cards["borja"]["latest"] is None
