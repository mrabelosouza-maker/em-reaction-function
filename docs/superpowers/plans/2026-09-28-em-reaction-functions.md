# EM Reaction Functions (v1 Banxico) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Um site estático no GitHub Pages que mostra a série hawk-dove do Board do Banxico (comunicados + atas desde jan/2025) e, quando houver, as falas/calls de membros contra essa série.

**Architecture:** Costura JSON, como em `Modelagem\fomc_reaction_functions`: agentes Claude (`claude -p`) classificam cada documento e gravam `data/<bc>/extracted/<speech_id>.json`; o pacote Python `emrf/` (determinístico, sem rede, sem LLM) valida os JSON, monta a série do Board, o heatmap e os cards, e escreve um HTML único com os dados embutidos, desenhado no navegador com Plotly. Coleta de comunicados vem do `_historico` local; minutas são raspadas do banxico.org.mx.

**Tech Stack:** Python 3 (stdlib + `pymupdf` para PDF), pytest, Plotly.js via CDN, git + GitHub Pages, `claude` CLI headless.

Spec: `docs/superpowers/specs/2026-09-28-em-reaction-functions-design.md`.

## Global Constraints

- Raiz do projeto: `R:\Macro EMs\Modelagem\em_reaction_functions` (todos os caminhos abaixo são relativos a ela). Rode Python pelo PowerShell a partir da raiz.
- Escopo v1: só `banxico`; só `comunicado` e `ata`; só documentos com `meeting_date >= 2025-01-01`.
- Rubrica: `1.0-generic` da skill `bc-hawk-dove` (`C:\Users\mrabelo\.claude\skills\bc-hawk-dove\references\rubrica.json`), copiada para `registry/rubric.json`.
- `null` = dimensão não coberta, nunca `0`. Scores inteiros ou `.5`.
- `emrf/` nunca chama modelo nem rede.
- `speech_id` segue a fórmula da skill (`bc_base.py speech_id`): `<slug(member_id)>-YYYYMMDD-<sha1(title.strip().lower())[:6]>`. Colegiado usa `member_id="board"` e título canônico `"Comunicado <meeting_date>"` / `"Minuta <meeting_date>"`.
- Nunca editar/apagar arquivo em `data/<bc>/raw/` depois de gravado.
- Nunca `git add -A` / `git add .`.
- Publicação: GitHub Pages da raiz de `main`; `index.html` entra no git como blob de `results/index.html` (`git hash-object -w` + `update-index`), nunca a partir do working tree (o share R: trunca arquivos grandes).
- Tudo é público, inclusive calls privados (decisão do analista).
- No máximo 2 processos `claude -p` simultâneos.
- Commits terminam com `Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>`.

## File Structure

```
emrf/__init__.py          # vazio
emrf/config.py            # caminhos, BCs, dimensões, enums, DRIVER_IDS (lidos da rubrica)
emrf/schema.py            # speech_id, colegiado_id, Record, validate, load_records
emrf/board.py             # board_series, board_level_at, member_points, heatmap, kpis, member_cards
emrf/build.py             # bc_payload, build() -> results/index.html
emrf/html.py              # render(payload, generated) -> str (template + JS)
emrf/coleta_banxico.py    # parse_minutas, raw_header, pendentes (funções puras testáveis)
scripts/build.py          # CLI: python scripts/build.py
scripts/coletar_banxico.py# CLI: coleta comunicados (_historico) + minutas (site) -> raw/
scripts/classificar.py    # CLI: roda claude -p para cada pendente
agents/10_classificar_colegiado.md
registry/rubric.json
registry/banxico/roster.json
tests/conftest.py tests/test_schema.py tests/test_board.py tests/test_build.py tests/test_coleta.py
CLAUDE.md  requirements.txt  .gitignore  .nojekyll
```

Mudança em relação ao spec §4: não há `registry/<bc>/calendar.json` — as reuniões são as `meeting_date` dos comunicados (YAGNI). Não há `emrf/html.py` separado de lógica: `html.py` só formata.

---

### Task 1: Esqueleto, config e schema

**Files:**
- Create: `emrf/__init__.py`, `emrf/config.py`, `emrf/schema.py`, `registry/rubric.json`, `requirements.txt`, `.gitignore`, `.nojekyll`
- Test: `tests/conftest.py`, `tests/test_schema.py`

**Interfaces:**
- Produces:
  - `config.ROOT, DATA, REGISTRY, RESULTS: Path`; `config.START_DATE = "2025-01-01"`; `config.BCS: dict[str, dict]`; `config.DIMENSIONS: dict[str, tuple[int,int]]`; `config.TRACKS: dict[str, set[str]]`; `config.DOC_ORDER: dict[str,int]`; `config.DIRECTIONS, ACTIONS, PUSHES: set[str]`; `config.BOARD_ID = "board"`; `config.DRIVER_IDS: list[str]`; `config.extracted_dir(bc) -> Path`; `config.raw_dir(bc) -> Path`
  - `schema.SchemaError(ValueError)`; `schema.slugify(s) -> str`; `schema.speech_id(member_id, date, title) -> str`; `schema.colegiado_title(doc_type, meeting_date) -> str`; `schema.colegiado_id(doc_type, date, meeting_date) -> str`; `schema.Record` (dataclass, `.composite -> float|None`, `.validate() -> Record`, `Record.from_json(d) -> Record`); `schema.load_records(bc, folder: Path|None=None) -> list[Record]` ordenada por `(date, DOC_ORDER[doc_type])`
  - fixture pytest `make_record(**overrides) -> dict` (JSON válido de comunicado)

- [ ] **Step 1: Criar arquivos de suporte**

```powershell
New-Item -ItemType Directory -Force emrf, tests, scripts, agents, registry\banxico, data\banxico\raw, data\banxico\extracted, results | Out-Null
Copy-Item "C:\Users\mrabelo\.claude\skills\bc-hawk-dove\references\rubrica.json" registry\rubric.json
New-Item -ItemType File emrf\__init__.py, .nojekyll | Out-Null
```

`requirements.txt`:
```
pymupdf>=1.24
pytest>=7.0
```

`pytest.ini`:
```
[pytest]
pythonpath = .
testpaths = tests
```

`.gitignore`:
```
__pycache__/
*.pyc
.pytest_cache/
results/
```

- [ ] **Step 2: Escrever `emrf/config.py`**

```python
"""Caminhos, BCs e vocabulário fechado do contrato JSON."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
REGISTRY = ROOT / "registry"
RESULTS = ROOT / "results"

START_DATE = "2025-01-01"

BCS = {
    "banxico": {"label": "Banxico", "pais": "México"},
    "bcch": {"label": "BCCh", "pais": "Chile"},
    "banrep": {"label": "BanRep", "pais": "Colômbia"},
    "sarb": {"label": "SARB", "pais": "África do Sul"},
}

DIMENSIONS = {
    "composite_hawk_dove": (-5, 5),
    "mandate_weight": (-5, 5),
    "inflation_conviction": (0, 5),
    "labor_concern": (0, 5),
    "policy_stance_read": (0, 5),
}

TRACKS = {
    "colegiado": {"comunicado", "ata", "rti"},
    "membro": {"fala_publica", "call_privado"},
}
DOC_ORDER = {"comunicado": 0, "ata": 1, "rti": 2, "fala_publica": 3, "call_privado": 4}

DIRECTIONS = {"cut", "hold", "hike", "unclear"}
ACTIONS = {"cut", "hold", "hike"}
PUSHES = {"hawkish", "dovish", "neutral"}

BOARD_ID = "board"

RUBRIC = json.loads((REGISTRY / "rubric.json").read_text(encoding="utf-8"))
DRIVER_IDS = [i["id"] for i in RUBRIC["drivers"]["items"]]


def extracted_dir(bc: str) -> Path:
    return DATA / bc / "extracted"


def raw_dir(bc: str) -> Path:
    return DATA / bc / "raw"
```

- [ ] **Step 3: Escrever `tests/conftest.py`**

```python
import copy

import pytest

from emrf import schema

_BASE = {
    "bc": "banxico",
    "track": "colegiado",
    "doc_type": "comunicado",
    "member_id": "board",
    "date": "2026-09-24",
    "meeting_date": "2026-09-24",
    "url": "https://www.banxico.org.mx/",
    "source": "banxico",
    "non_policy": False,
    "decision": {"action": "hold", "rate": "6.50%", "vote": "5-0", "dissents": []},
    "summary": "The Board held.",
    "key_quotes": [
        {"quote": "a", "context": "c", "dimension": "composite_hawk_dove"},
        {"quote": "b", "context": "c", "dimension": "near_term_bias"},
    ],
    "llm_scores": {
        "composite_hawk_dove": 0.5, "mandate_weight": 1, "inflation_conviction": 3,
        "labor_concern": 2, "policy_stance_read": 3,
        "near_term_bias": {"direction": "hold", "pace": "data-dependent"},
        "theme_flags": [],
    },
    "drivers": {d: {"intensity": 1, "push": "neutral"} for d in
                ["supply_shocks", "underlying_inflation", "fx_external",
                 "labor_market", "growth_demand", "other"]},
    "extractor_model": "test", "extracted_at": "2026-09-28T00:00:00Z",
    "rubric_version": "1.0-generic",
}


def _make(**over) -> dict:
    d = copy.deepcopy(_BASE)
    composite = over.pop("composite", "keep")
    d.update(over)
    if composite != "keep":
        d["llm_scores"]["composite_hawk_dove"] = composite
    if d["track"] == "colegiado" and d["doc_type"] in ("comunicado", "ata", "rti"):
        d["title"] = schema.colegiado_title(d["doc_type"], d["meeting_date"])
    elif d["track"] == "colegiado":
        d["title"] = f"Doc {d['date']}"  # doc_type inválido: o teste espera falha de schema
    else:
        d.setdefault("title", f"Call {d['date']}")
        d.pop("meeting_date", None)
        d.pop("decision", None)
    d["speech_id"] = schema.speech_id(d["member_id"], d["date"], d["title"])
    return d


@pytest.fixture
def make_record():
    return _make
```

- [ ] **Step 4: Escrever os testes que falham — `tests/test_schema.py`**

```python
import json

import pytest

from emrf import schema
from emrf.schema import Record, SchemaError, load_records


def test_speech_id_matches_skill_formula():
    # mesmo algoritmo de bc_base.py: sha1 do título em minúsculas, 6 hex
    assert schema.speech_id("Heath", "2026-09-24", "X") == "heath-20260924-11f6ad"


def test_colegiado_id_is_deterministic():
    a = schema.colegiado_id("ata", "2026-10-08", "2026-09-24")
    assert a == schema.speech_id("board", "2026-10-08", "Minuta 2026-09-24")


def test_valid_record_passes(make_record):
    r = Record.from_json(make_record()).validate()
    assert r.composite == 0.5


def test_null_composite_allowed(make_record):
    assert Record.from_json(make_record(composite=None)).validate().composite is None


@pytest.mark.parametrize("over, msg", [
    ({"composite": 6}, "fora de"),
    ({"doc_type": "call_privado"}, "não pertence"),
    ({"bc": "fed"}, "bc"),
])
def test_invalid_records_fail(make_record, over, msg):
    d = make_record(**over)
    with pytest.raises(SchemaError, match=msg):
        Record.from_json(d).validate()


def test_colegiado_requires_decision(make_record):
    d = make_record()
    d["decision"] = None
    with pytest.raises(SchemaError, match="decision"):
        Record.from_json(d).validate()


def test_wrong_id_fails(make_record):
    d = make_record()
    d["speech_id"] = "board-20260924-000000"
    with pytest.raises(SchemaError, match="id"):
        Record.from_json(d).validate()


def test_drivers_must_match_rubric(make_record):
    d = make_record()
    del d["drivers"]["other"]
    with pytest.raises(SchemaError, match="drivers"):
        Record.from_json(d).validate()


def test_membro_cannot_be_board(make_record):
    d = make_record(track="membro", doc_type="call_privado", member_id="board")
    with pytest.raises(SchemaError, match="board"):
        Record.from_json(d).validate()


def test_load_records_sorted_and_names_bad_file(tmp_path, make_record):
    ata = make_record(doc_type="ata", date="2026-10-08")
    com = make_record()
    for d in (ata, com):
        (tmp_path / f"{d['speech_id']}.json").write_text(json.dumps(d), encoding="utf-8")
    recs = load_records("banxico", tmp_path)
    assert [r.doc_type for r in recs] == ["comunicado", "ata"]
    bad = make_record(composite=9)
    (tmp_path / f"{bad['speech_id']}x.json").write_text(json.dumps(bad), encoding="utf-8")
    with pytest.raises(SchemaError, match=bad["speech_id"]):
        load_records("banxico", tmp_path)
```

- [ ] **Step 5: Rodar e ver falhar**

Run: `python -m pytest tests/test_schema.py -q`
Expected: FAIL (`ImportError: cannot import name 'schema'`)

- [ ] **Step 6: Escrever `emrf/schema.py`**

```python
"""Contrato JSON entre os agentes (não determinísticos) e o build (determinístico).

Validação estrita: saída ruim de agente tem que falhar aqui, com o nome do arquivo,
e não virar um gráfico errado.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import config

_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
_COLEGIADO_TITLE = {"comunicado": "Comunicado", "ata": "Minuta", "rti": "Informe Trimestral"}
REQUIRED = ("speech_id", "bc", "track", "doc_type", "member_id", "title", "date",
            "summary", "key_quotes", "llm_scores", "drivers")


class SchemaError(ValueError):
    pass


def _require(cond: bool, msg: str) -> None:
    if not cond:
        raise SchemaError(msg)


def slugify(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def speech_id(member_id: str, date: str, title: str) -> str:
    """Mesma fórmula de bc_base.py da skill bc-hawk-dove."""
    h = hashlib.sha1(title.strip().lower().encode("utf-8")).hexdigest()[:6]
    return f"{slugify(member_id)}-{date.replace('-', '')}-{h}"


def colegiado_title(doc_type: str, meeting_date: str) -> str:
    return f"{_COLEGIADO_TITLE[doc_type]} {meeting_date}"


def colegiado_id(doc_type: str, date: str, meeting_date: str) -> str:
    return speech_id(config.BOARD_ID, date, colegiado_title(doc_type, meeting_date))


@dataclass
class Record:
    speech_id: str
    bc: str
    track: str
    doc_type: str
    member_id: str
    title: str
    date: str
    summary: str
    key_quotes: list[dict]
    llm_scores: dict[str, Any]
    drivers: dict[str, Any]
    url: str = ""
    source: str = ""
    non_policy: bool = False
    meeting_date: str | None = None
    decision: dict | None = None
    extractor_model: str = ""
    extracted_at: str = ""
    rubric_version: str = ""

    @property
    def composite(self) -> float | None:
        return self.llm_scores.get("composite_hawk_dove")

    @staticmethod
    def from_json(d: dict) -> "Record":
        missing = [k for k in REQUIRED if k not in d]
        _require(not missing, f"{d.get('speech_id', '?')}: campos ausentes {missing}")
        names = {f.name for f in dataclasses.fields(Record)}
        return Record(**{k: v for k, v in d.items() if k in names})

    def validate(self) -> "Record":
        sid = self.speech_id
        _require(self.bc in config.BCS, f"{sid}: bc {self.bc!r} desconhecido")
        _require(self.track in config.TRACKS, f"{sid}: track {self.track!r} inválida")
        _require(self.doc_type in config.TRACKS[self.track],
                 f"{sid}: doc_type {self.doc_type!r} não pertence à trilha {self.track}")
        _require(_DATE.fullmatch(self.date) is not None, f"{sid}: date {self.date!r}")
        _require(sid == speech_id(self.member_id, self.date, self.title),
                 f"{sid}: id inconsistente com member_id/date/title")
        if self.track == "colegiado":
            _require(self.member_id == config.BOARD_ID, f"{sid}: colegiado exige member_id board")
            _require(bool(self.meeting_date) and _DATE.fullmatch(self.meeting_date) is not None,
                     f"{sid}: meeting_date {self.meeting_date!r}")
            _require(self.meeting_date <= self.date, f"{sid}: meeting_date depois de date")
            _require(isinstance(self.decision, dict) and self.decision.get("action") in config.ACTIONS,
                     f"{sid}: decision inválida {self.decision!r}")
        else:
            _require(self.member_id != config.BOARD_ID, f"{sid}: membro não pode ser board")
        for dim, (lo, hi) in config.DIMENSIONS.items():
            v = self.llm_scores.get(dim)
            ok = v is None or (isinstance(v, (int, float)) and not isinstance(v, bool) and lo <= v <= hi)
            _require(ok, f"{sid}: {dim}={v!r} fora de [{lo},{hi}]")
        bias = self.llm_scores.get("near_term_bias") or {}
        _require(bias.get("direction") in config.DIRECTIONS | {None},
                 f"{sid}: near_term_bias.direction {bias.get('direction')!r}")
        _require(set(self.drivers) == set(config.DRIVER_IDS),
                 f"{sid}: drivers devem ser {config.DRIVER_IDS}")
        for k, v in self.drivers.items():
            _require(v.get("intensity") in (0, 1, 2, 3) and v.get("push") in config.PUSHES,
                     f"{sid}: driver {k} inválido {v!r}")
        return self


def load_records(bc: str, folder: Path | None = None) -> list[Record]:
    folder = Path(folder or config.extracted_dir(bc))
    out = []
    for p in sorted(folder.glob("*.json")):
        try:
            r = Record.from_json(json.loads(p.read_text(encoding="utf-8"))).validate()
        except (SchemaError, TypeError, json.JSONDecodeError) as e:
            raise SchemaError(f"{p.name}: {e}") from e
        _require(r.bc == bc, f"{p.name}: bc {r.bc} != {bc}")
        _require(p.stem == r.speech_id, f"{p.name}: nome difere do speech_id {r.speech_id}")
        out.append(r)
    return sorted(out, key=lambda r: (r.date, config.DOC_ORDER[r.doc_type]))
```

- [ ] **Step 7: Rodar e ver passar**

Run: `python -m pytest tests/test_schema.py -q`
Expected: todos PASS. Se `test_speech_id_matches_skill_formula` falhar, confira o valor com `python C:\Users\mrabelo\.claude\skills\bc-hawk-dove\scripts\bc_base.py id Heath 2026-09-24 X` e corrija o literal do teste para o que a skill imprime (a skill é a referência).

- [ ] **Step 8: Commit**

```powershell
git add emrf/__init__.py emrf/config.py emrf/schema.py registry/rubric.json requirements.txt pytest.ini .gitignore .nojekyll tests/conftest.py tests/test_schema.py
git commit -m "feat: contrato JSON (schema, config, rubrica 1.0-generic)`n`nCo-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: Série do Board, desvio, heatmap, KPIs e cards

**Files:**
- Create: `emrf/board.py`
- Test: `tests/test_board.py`

**Interfaces:**
- Consumes: `schema.Record` (`.track`, `.doc_type`, `.date`, `.meeting_date`, `.composite`, `.non_policy`, `.member_id`, `.decision`, `.key_quotes`, `.speech_id`), `config.BOARD_ID`
- Produces:
  - `board_series(records: list[Record]) -> list[dict]` — itens `{"date","level","doc_type","meeting_date","speech_id"}`
  - `board_level_at(series, date: str) -> float|None`
  - `member_points(records, series) -> list[dict]` — itens `{"date","member_id","doc_type","composite","board","deviation","speech_id"}`
  - `meetings(records) -> list[str]`
  - `heatmap(records, series, members: list[str], today: str) -> {"columns": list[str], "board": list, "level": {mid: list}, "deviation": {mid: list}}`
  - `kpis(records, series) -> dict` com chaves `rate, action, vote, dissents, meeting_date, board_level, board_delta, last_doc_type, last_doc_date`
  - `member_cards(records, series, roster: list[dict]) -> list[dict]` com chaves `member_id, name, role, latest, date, doc_type, delta, deviation, quote`

- [ ] **Step 1: Escrever os testes que falham — `tests/test_board.py`**

```python
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
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests/test_board.py -q`
Expected: FAIL (`ImportError: cannot import name 'board'`)

- [ ] **Step 3: Escrever `emrf/board.py`**

```python
"""Série do Board (degrau), desvio dos membros, heatmap por ciclo, KPIs e cards.

Nível do Board em t = composto do último documento colegiado com date <= t.
Documento com composto null não move o degrau. Desvio = membro - Board vigente.
"""
from __future__ import annotations

from bisect import bisect_right
from datetime import date as _date, timedelta
from statistics import mean

from .schema import Record


def _avg(xs: list[float]) -> float | None:
    return round(mean(xs), 2) if xs else None


def _day_before(d: str) -> str:
    return (_date.fromisoformat(d) - timedelta(days=1)).isoformat()


def _policy_members(records: list[Record]) -> list[Record]:
    return [r for r in records
            if r.track == "membro" and not r.non_policy and r.composite is not None]


def board_series(records: list[Record]) -> list[dict]:
    return [{"date": r.date, "level": r.composite, "doc_type": r.doc_type,
             "meeting_date": r.meeting_date, "speech_id": r.speech_id}
            for r in records if r.track == "colegiado" and r.composite is not None]


def board_level_at(series: list[dict], date: str) -> float | None:
    i = bisect_right([p["date"] for p in series], date)
    return series[i - 1]["level"] if i else None


def member_points(records: list[Record], series: list[dict]) -> list[dict]:
    out = []
    for r in _policy_members(records):
        b = board_level_at(series, r.date)
        out.append({"date": r.date, "member_id": r.member_id, "doc_type": r.doc_type,
                    "composite": r.composite, "board": b,
                    "deviation": None if b is None else r.composite - b,
                    "speech_id": r.speech_id})
    return out


def meetings(records: list[Record]) -> list[str]:
    return sorted({r.meeting_date for r in records if r.doc_type == "comunicado"})


def heatmap(records: list[Record], series: list[dict], members: list[str], today: str) -> dict:
    ms = meetings(records)
    pts = member_points(records, series)
    board_row: list = []
    level = {m: [] for m in members}
    dev = {m: [] for m in members}
    for k, start in enumerate(ms):
        end = ms[k + 1] if k + 1 < len(ms) else None
        board_row.append(board_level_at(series, _day_before(end) if end else today))
        for mid in members:
            ps = [p for p in pts if p["member_id"] == mid
                  and start <= p["date"] and (end is None or p["date"] < end)]
            level[mid].append(_avg([p["composite"] for p in ps]))
            dev[mid].append(_avg([p["deviation"] for p in ps if p["deviation"] is not None]))
    return {"columns": ms, "board": board_row, "level": level, "deviation": dev}


def kpis(records: list[Record], series: list[dict]) -> dict:
    coms = [r for r in records if r.doc_type == "comunicado"]
    last = coms[-1] if coms else None
    dec = (last.decision or {}) if last else {}
    return {
        "rate": dec.get("rate"), "action": dec.get("action"), "vote": dec.get("vote"),
        "dissents": dec.get("dissents", []),
        "meeting_date": last.meeting_date if last else None,
        "board_level": series[-1]["level"] if series else None,
        "board_delta": series[-1]["level"] - series[-2]["level"] if len(series) > 1 else None,
        "last_doc_type": series[-1]["doc_type"] if series else None,
        "last_doc_date": series[-1]["date"] if series else None,
    }


def member_cards(records: list[Record], series: list[dict], roster: list[dict]) -> list[dict]:
    pol = _policy_members(records)
    cards = []
    for m in roster:
        rs = [r for r in pol if r.member_id == m["member_id"]]
        card = {"member_id": m["member_id"], "name": m["name"], "role": m.get("role", ""),
                "latest": None, "date": None, "doc_type": None, "delta": None,
                "deviation": None, "quote": ""}
        if rs:
            last, prev = rs[-1], (rs[-2] if len(rs) > 1 else None)
            b = board_level_at(series, last.date)
            card.update(latest=last.composite, date=last.date, doc_type=last.doc_type,
                        delta=None if prev is None else last.composite - prev.composite,
                        deviation=None if b is None else last.composite - b,
                        quote=last.key_quotes[0]["quote"] if last.key_quotes else "")
        cards.append(card)
    return cards
```

- [ ] **Step 4: Rodar e ver passar**

Run: `python -m pytest tests/test_board.py -q`
Expected: 5 passed

- [ ] **Step 5: Commit**

```powershell
git add emrf/board.py tests/test_board.py
git commit -m "feat: serie do Board em degrau, desvio, heatmap, KPIs e cards`n`nCo-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: Build e HTML

**Files:**
- Create: `emrf/build.py`, `emrf/html.py`, `scripts/build.py`, `registry/banxico/roster.json`
- Test: `tests/test_build.py`

**Interfaces:**
- Consumes: `schema.load_records`, `schema.SchemaError`, tudo de `board`, `config.BCS/REGISTRY/RESULTS/raw_dir`
- Produces:
  - `build.load_roster(bc) -> list[dict]` (lê `registry/<bc>/roster.json`, chave `members`)
  - `build.bc_payload(bc, records, roster, raw_folder: Path, today: str) -> dict` com chaves `label, pais, kpis, series, members, points, heatmap, cards, docs`
  - `build.build(today: str|None=None, out: Path|None=None, extracted_root: Path|None=None, raw_root: Path|None=None) -> Path` — `extracted_root/raw_root` são pastas-pai com uma subpasta por BC (para teste); default `config.DATA`
  - `html.render(payload: dict, generated: str) -> str` — dados em `<script id="data" type="application/json">`

- [ ] **Step 1: Verificar a composição atual da Junta e gravar `registry/banxico/roster.json`**

Consulte `https://www.banxico.org.mx/acerca-del-banco-de-mexico/junta-de-gobierno.html` (WebFetch) e liste os 5 membros atuais. **Não preencha de memória** — mandatos mudam (ex.: um subgovernador sai em dezembro). Formato (`member_id` = sobrenome em minúsculas sem acento, igual à skill):

```json
{
  "verified_at": "2026-09-28",
  "source": "https://www.banxico.org.mx/acerca-del-banco-de-mexico/junta-de-gobierno.html",
  "members": [
    {"member_id": "rodriguez", "name": "Victoria Rodríguez Ceja", "role": "Gobernadora"}
  ]
}
```
(o exemplo mostra um item; grave os 5 verificados.)

- [ ] **Step 2: Escrever o teste que falha — `tests/test_build.py`**

```python
import json
import re

import pytest

from emrf import build
from emrf.schema import SchemaError


def _write(root, d):
    folder = root / d["bc"] / "extracted"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{d['speech_id']}.json").write_text(json.dumps(d), encoding="utf-8")


def _data(html):
    m = re.search(r'<script id="data" type="application/json">(.*?)</script>', html, re.S)
    return json.loads(m.group(1).replace("<\\/", "</"))


def test_build_smoke(tmp_path, make_record):
    ext, raw = tmp_path / "ext", tmp_path / "raw"
    com = make_record(composite=-0.5)
    ata = make_record(doc_type="ata", date="2026-10-08", composite=0.0)
    for d in (com, ata):
        _write(ext, d)
    (raw / "banxico" / "raw").mkdir(parents=True)
    (raw / "banxico" / "raw" / f"{com['speech_id']}.md").write_text("texto </script> cru", encoding="utf-8")
    out = build.build(today="2026-10-20", out=tmp_path / "index.html",
                      extracted_root=ext, raw_root=raw)
    html = out.read_text(encoding="utf-8")
    data = _data(html)
    assert list(data["bcs"]) == ["banxico"]            # só BC com dados vira aba
    bx = data["bcs"]["banxico"]
    assert {d["speech_id"] for d in bx["docs"]} == {com["speech_id"], ata["speech_id"]}
    assert [p["level"] for p in bx["series"]] == [-0.5, 0.0]
    assert "texto </script> cru" in [d["text"] for d in bx["docs"] if d["speech_id"] == com["speech_id"]][0]
    assert "Metodologia" in html


def test_build_rejects_member_outside_roster(tmp_path, make_record):
    ext = tmp_path / "ext"
    _write(ext, make_record())
    _write(ext, make_record(track="membro", doc_type="call_privado",
                            member_id="fulano", date="2026-09-30"))
    with pytest.raises(SchemaError, match="fulano"):
        build.build(today="2026-10-20", out=tmp_path / "i.html",
                    extracted_root=ext, raw_root=tmp_path)
```

- [ ] **Step 3: Rodar e ver falhar**

Run: `python -m pytest tests/test_build.py -q`
Expected: FAIL (`ImportError: cannot import name 'build'`)

- [ ] **Step 4: Escrever `emrf/build.py`**

```python
"""Lê os JSON de cada BC, monta o payload e escreve o HTML único."""
from __future__ import annotations

import dataclasses
import json
from datetime import date
from pathlib import Path

from . import board, config, html
from .schema import SchemaError, load_records


def load_roster(bc: str) -> list[dict]:
    p = config.REGISTRY / bc / "roster.json"
    return json.loads(p.read_text(encoding="utf-8"))["members"] if p.exists() else []


def bc_payload(bc: str, records, roster: list[dict], raw_folder: Path, today: str) -> dict:
    known = {m["member_id"] for m in roster}
    for r in records:
        if r.track == "membro" and r.member_id not in known:
            raise SchemaError(f"{r.speech_id}: member_id {r.member_id} fora de registry/{bc}/roster.json")
    series = board.board_series(records)
    members = [m["member_id"] for m in roster]
    docs = []
    for r in records:
        raw = raw_folder / f"{r.speech_id}.md"
        d = dataclasses.asdict(r)
        d["text"] = raw.read_text(encoding="utf-8") if raw.exists() else ""
        docs.append(d)
    return {
        **config.BCS[bc],
        "kpis": board.kpis(records, series),
        "series": series,
        "members": roster,
        "points": board.member_points(records, series),
        "heatmap": board.heatmap(records, series, members, today),
        "cards": board.member_cards(records, series, roster),
        "docs": docs,
    }


def build(today: str | None = None, out: Path | None = None,
          extracted_root: Path | None = None, raw_root: Path | None = None) -> Path:
    today = today or date.today().isoformat()
    out = Path(out or config.RESULTS / "index.html")
    extracted_root = Path(extracted_root or config.DATA)
    raw_root = Path(raw_root or config.DATA)
    bcs = {}
    for bc in config.BCS:
        folder = extracted_root / bc / "extracted"
        records = load_records(bc, folder) if folder.exists() else []
        if records:
            bcs[bc] = bc_payload(bc, records, load_roster(bc), raw_root / bc / "raw", today)
    if not bcs:
        raise SchemaError("nenhum BC com documentos classificados")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html.render({"bcs": bcs}, generated=today), encoding="utf-8")
    return out
```

- [ ] **Step 5: Escrever `emrf/html.py`**

```python
"""Template do site. Só formatação: toda a lógica está em board.py/build.py."""
from __future__ import annotations

import json

TEMPLATE = r"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>EM Reaction Functions</title>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
:root{--bg:#faf8f3;--fg:#1d1d1b;--muted:#6b6b66;--card:#fff;--line:#e3dfd5;--hawk:#b2182b;--dove:#2166ac;--accent:#1f5f3f}
@media (prefers-color-scheme:dark){:root{--bg:#141414;--fg:#eee;--muted:#9a9a95;--card:#1e1e1e;--line:#333;--accent:#6fbf8f}}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,-apple-system,Segoe UI,sans-serif}
header{padding:16px;border-bottom:1px solid var(--line)}header h1{margin:0;font-size:20px}header p{margin:4px 0 0;color:var(--muted);font-size:13px}
nav{display:flex;gap:4px;padding:8px 16px;border-bottom:1px solid var(--line);position:sticky;top:0;background:var(--bg);z-index:5;overflow-x:auto}
nav button{border:1px solid var(--line);background:var(--card);color:var(--fg);padding:6px 14px;border-radius:999px;cursor:pointer}
nav button.on{background:var(--accent);color:#fff;border-color:var(--accent)}
main{max-width:1100px;margin:0 auto;padding:16px}section.tab{display:none}section.tab.on{display:block}
h2{font-size:17px;margin:28px 0 8px}.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:10px}
.kpi,.card{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:12px}
.kpi b{display:block;font-size:22px}.kpi span{color:var(--muted);font-size:12px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:10px}
.card q{display:block;color:var(--muted);font-size:13px;margin-top:6px}.tag{font-size:11px;border:1px solid var(--line);border-radius:4px;padding:0 5px;margin-left:4px}
.pos{color:var(--hawk)}.neg{color:var(--dove)}.chart{background:var(--card);border:1px solid var(--line);border-radius:8px;min-height:360px}
.filters{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:8px}.filters input,.filters select{padding:6px;border:1px solid var(--line);border-radius:6px;background:var(--card);color:var(--fg)}
details{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:8px 12px;margin-bottom:6px}
details pre{white-space:pre-wrap;font:13px/1.45 inherit;max-height:420px;overflow:auto}
</style></head><body>
<header><h1>EM Reaction Functions</h1><p>Escala hawk-dove de comunicação de BCs emergentes · colegiado × membros · gerado em __GENERATED__</p></header>
<nav id="nav"></nav><main id="main"></main>
<script id="data" type="application/json">__DATA__</script>
<script>
const DATA = JSON.parse(document.getElementById('data').textContent);
const DOC = {comunicado:'Comunicado', ata:'Ata', rti:'RTI', fala_publica:'Fala pública', call_privado:'Call privado'};
const SYM = {comunicado:'circle', ata:'square', rti:'triangle-up'};
const ACT = {cut:'corte', hold:'manutenção', hike:'alta'};
const fmt = v => v == null ? '—' : (v > 0 ? '+' : '') + v.toFixed(1);
const cls = v => v == null ? '' : v > 0 ? 'pos' : v < 0 ? 'neg' : '';
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const dark = matchMedia('(prefers-color-scheme: dark)').matches;
const LAYOUT = {paper_bgcolor:'rgba(0,0,0,0)', plot_bgcolor:'rgba(0,0,0,0)', font:{color: dark ? '#eee' : '#1d1d1b'},
  margin:{l:50, r:20, t:20, b:40}, legend:{orientation:'h', y:-0.15}};

function kpiHtml(k) {
  return `<div class="kpis">
    <div class="kpi"><span>Taxa</span><b>${esc(k.rate ?? '—')}</b><span>${esc(ACT[k.action] ?? '')} em ${esc(k.meeting_date ?? '')}</span></div>
    <div class="kpi"><span>Votação</span><b>${esc(k.vote ?? '—')}</b><span>${esc((k.dissents || []).join('; '))}</span></div>
    <div class="kpi"><span>Nível do Board</span><b class="${cls(k.board_level)}">${fmt(k.board_level)}</b><span>${esc(DOC[k.last_doc_type] ?? '')} de ${esc(k.last_doc_date ?? '')}</span></div>
    <div class="kpi"><span>Δ vs documento anterior</span><b class="${cls(k.board_delta)}">${fmt(k.board_delta)}</b></div></div>`;
}

function boardChart(el, b) {
  const names = Object.fromEntries(b.members.map(m => [m.member_id, m.name]));
  const traces = [{x: b.series.map(p => p.date), y: b.series.map(p => p.level), name: 'Board',
    mode: 'lines+markers', line: {shape: 'hv', width: 3, color: '#1f5f3f'},
    marker: {size: 10, symbol: b.series.map(p => SYM[p.doc_type])},
    text: b.series.map(p => DOC[p.doc_type] + ' (reunião ' + p.meeting_date + ')'), hovertemplate: '%{text}<br>%{y:+.1f}<extra></extra>'}];
  for (const m of b.members) {
    const ps = b.points.filter(p => p.member_id === m.member_id);
    if (!ps.length) continue;
    traces.push({x: ps.map(p => p.date), y: ps.map(p => p.composite), name: m.name, mode: 'markers',
      marker: {size: 9, symbol: ps.map(p => p.doc_type === 'call_privado' ? 'diamond' : 'circle-open')},
      text: ps.map(p => DOC[p.doc_type] + ' · desvio ' + fmt(p.deviation)), hovertemplate: '%{text}<br>%{y:+.1f}<extra>' + esc(m.name) + '</extra>'});
  }
  Plotly.newPlot(el, traces, {...LAYOUT, yaxis: {range: [-5, 5], zeroline: true, title: 'dove ← → hawk'}}, {responsive: true, displayModeBar: false});
}

function heatChart(el, b, mode) {
  const h = b.heatmap, rows = ['Board', ...b.members.map(m => m.name)];
  const z = [h.board, ...b.members.map(m => (mode === 'deviation' ? h.deviation : h.level)[m.member_id])];
  const lim = mode === 'deviation' ? 3 : 5;
  Plotly.newPlot(el, [{type: 'heatmap', x: h.columns, y: rows, z, zmin: -lim, zmax: lim,
    colorscale: [[0, '#2166ac'], [0.5, '#f7f7f7'], [1, '#b2182b']], hoverongaps: false,
    text: z.map(r => r.map(fmt)), texttemplate: '%{text}', hovertemplate: '%{y} · ciclo %{x}<br>%{text}<extra></extra>'}],
    {...LAYOUT, yaxis: {autorange: 'reversed'}, xaxis: {type: 'category'}}, {responsive: true, displayModeBar: false});
}

function cardsHtml(b) {
  return '<div class="cards">' + b.cards.map(c => `<div class="card"><b>${esc(c.name)}</b> <span class="tag">${esc(c.role)}</span><br>
    ${c.latest == null ? '<span style="color:var(--muted)">sem falas na base</span>' :
    `<span class="${cls(c.latest)}">${fmt(c.latest)}</span> · Δ ${fmt(c.delta)} · desvio vs Board <span class="${cls(c.deviation)}">${fmt(c.deviation)}</span>
     <span class="tag">${esc(DOC[c.doc_type])}</span> <span class="tag">${esc(c.date)}</span><q>${esc(c.quote)}</q>`}</div>`).join('') + '</div>';
}

function docsHtml(bc) {
  return `<div class="filters"><input id="q-${bc}" placeholder="buscar"><select id="t-${bc}"><option value="">todos os tipos</option>
    ${Object.entries(DOC).map(([k, v]) => `<option value="${k}">${v}</option>`).join('')}</select></div><div id="list-${bc}"></div>`;
}

function renderDocs(bc) {
  const q = document.getElementById('q-' + bc).value.toLowerCase(), t = document.getElementById('t-' + bc).value;
  const docs = DATA.bcs[bc].docs.filter(d => (!t || d.doc_type === t) &&
    (!q || (d.title + d.summary + d.text + d.member_id).toLowerCase().includes(q))).reverse();
  document.getElementById('list-' + bc).innerHTML = docs.map(d => `<details><summary>${esc(d.date)} · ${esc(DOC[d.doc_type])} ·
    ${esc(d.member_id === 'board' ? 'Board' : d.member_id)} · <b class="${cls(d.llm_scores.composite_hawk_dove)}">${fmt(d.llm_scores.composite_hawk_dove)}</b> — ${esc(d.title)}</summary>
    <p>${esc(d.summary)}</p><ul>${d.key_quotes.map(q => `<li><i>${esc(q.quote)}</i></li>`).join('')}</ul>
    ${d.url ? `<p><a href="${esc(d.url)}" target="_blank" rel="noopener">fonte</a></p>` : ''}<pre>${esc(d.text)}</pre></details>`).join('');
}

const METODO = `<h2>Metodologia</h2>
<p><b>Rubrica.</b> Cada documento é classificado por um modelo de linguagem na rubrica 1.0-generic (projeto de reaction functions do FOMC, drivers adaptados a EMs): composto hawk-dove em [−5, +5] (positivo = hawk), peso no mandato de preços, convicção sobre inflação, preocupação com atividade, leitura do stance, viés de curto prazo e seis drivers. Dimensão não tratada no texto fica em branco, nunca zero. Diferenças de 0,5 são ruído.</p>
<p><b>Duas trilhas.</b> <i>Colegiado</i> (comunicado e ata) é a voz oficial da Junta. <i>Membros</i> (falas públicas e calls privados) é a voz individual.</p>
<p><b>Série do Board.</b> Degrau: o nível em cada data é o composto do último documento colegiado publicado até ali (comunicado ou ata). Documento sem composto não move o degrau. <b>Ressalva:</b> comunicado e ata são gêneros diferentes — a ata é mais longa e explicita divisões —, então parte do salto comunicado→ata pode ser gênero, não mudança de postura. O marcador (● comunicado, ■ ata) permite separar.</p>
<p><b>Desvio do membro.</b> Composto da fala ou call menos o nível do Board vigente na data dela.</p>
<p><b>Heatmap.</b> Cada coluna é um ciclo entre duas reuniões. Board = nível no fim do ciclo (já com a ata). Membro = média das falas no ciclo; no modo desvio, média dos desvios.</p>
<p><b>Escopo.</b> Banxico, comunicados e atas desde janeiro de 2025. Outros BCs, RTIs e histórico de calls entram depois.</p>`;

function renderBC(bc, sec) {
  const b = DATA.bcs[bc];
  sec.innerHTML = kpiHtml(b.kpis) + `<h2>Board e membros</h2><div class="chart" id="bchart-${bc}"></div>
    <h2>Heatmap <select id="hm-${bc}"><option value="level">nível</option><option value="deviation">desvio vs Board</option></select></h2>
    <div class="chart" id="hchart-${bc}"></div><h2>Membros</h2>${cardsHtml(b)}<h2>Base de documentos</h2>${docsHtml(bc)}`;
  boardChart(document.getElementById('bchart-' + bc), b);
  const hm = document.getElementById('hm-' + bc);
  const drawHm = () => heatChart(document.getElementById('hchart-' + bc), b, hm.value);
  hm.onchange = drawHm; drawHm();
  document.getElementById('q-' + bc).oninput = () => renderDocs(bc);
  document.getElementById('t-' + bc).onchange = () => renderDocs(bc);
  renderDocs(bc);
}

const nav = document.getElementById('nav'), main = document.getElementById('main');
const tabs = [...Object.keys(DATA.bcs).map(bc => [bc, DATA.bcs[bc].label]), ['metodologia', 'Metodologia']];
const rendered = {};
function show(id) {
  for (const [k] of tabs) {
    document.getElementById('tab-' + k).classList.toggle('on', k === id);
    document.getElementById('btn-' + k).classList.toggle('on', k === id);
  }
  if (id !== 'metodologia' && !rendered[id]) { renderBC(id, document.getElementById('tab-' + id)); rendered[id] = true; }
  history.replaceState(null, '', '#' + id);
}
for (const [k, label] of tabs) {
  nav.insertAdjacentHTML('beforeend', `<button id="btn-${k}">${esc(label)}</button>`);
  main.insertAdjacentHTML('beforeend', `<section class="tab" id="tab-${k}">${k === 'metodologia' ? METODO : ''}</section>`);
  document.getElementById('btn-' + k).onclick = () => show(k);
}
show(tabs.some(([k]) => k === location.hash.slice(1)) ? location.hash.slice(1) : tabs[0][0]);
</script></body></html>
"""


def render(payload: dict, generated: str) -> str:
    blob = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    return TEMPLATE.replace("__GENERATED__", generated).replace("__DATA__", blob)
```

- [ ] **Step 6: Escrever `scripts/build.py`**

```python
"""Remonta results/index.html a partir de data/<bc>/extracted/. Grátis e reproduzível."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from emrf.build import build  # noqa: E402

if __name__ == "__main__":
    out = build()
    print(f"OK {out} ({out.stat().st_size / 1e6:.2f} MB)")
```

- [ ] **Step 7: Rodar e ver passar**

Run: `python -m pytest -q`
Expected: todos PASS (schema + board + build)

- [ ] **Step 8: Commit**

```powershell
git add emrf/build.py emrf/html.py scripts/build.py registry/banxico/roster.json tests/test_build.py
git commit -m "feat: build do site (abas por BC, Board+membros, heatmap, cards, base, metodologia)`n`nCo-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: Coleta de comunicados e minutas do Banxico

**Files:**
- Create: `emrf/coleta_banxico.py`, `scripts/coletar_banxico.py`
- Test: `tests/test_coleta.py`

**Interfaces:**
- Consumes: `schema.colegiado_id`, `config.START_DATE`, `config.raw_dir`, `config.extracted_dir`
- Produces:
  - `coleta_banxico.parse_minutas(html: str) -> list[dict]` com `{"date": pub YYYY-MM-DD, "meeting_date": YYYY-MM-DD, "url": absoluto}`
  - `coleta_banxico.raw_header(doc_type, date, meeting_date, url) -> str` (cabeçalho markdown com `speech_id`)
  - `coleta_banxico.read_meta(path: Path) -> dict` (lê os `<!-- chave: valor -->` do cabeçalho)
  - `coleta_banxico.pendentes(raw_folder: Path, extracted_folder: Path) -> list[Path]` (raw sem JSON, ordenados)
  - CLI `python scripts/coletar_banxico.py` — idempotente; imprime `PENDENTE <arquivo>` por pendente; exit 0

- [ ] **Step 1: Escrever os testes que falham — `tests/test_coleta.py`**

```python
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
    rows = cb.parse_minutas(SNIPPET)
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
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests/test_coleta.py -q`
Expected: FAIL (`ImportError`)

- [ ] **Step 3: Escrever `emrf/coleta_banxico.py`**

```python
"""Funções puras da coleta do Banxico (a rede fica no script)."""
from __future__ import annotations

import re
from pathlib import Path

from .schema import colegiado_id, colegiado_title

BASE = "https://www.banxico.org.mx"
MESES = {m: i for i, m in enumerate(
    ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
     "septiembre", "octubre", "noviembre", "diciembre"], start=1)}
_ROW = re.compile(
    r"aria-hidden=true>(\d{2})/(\d{2})/(\d{2}).*?anunciada el (\d{1,2}) de (\w+) de (\d{4}).*?HREF=\"([^\"]+\.pdf)\"",
    re.S | re.I)
_META = re.compile(r"<!--\s*(\w+):\s*(.*?)\s*-->")


def parse_minutas(html: str) -> list[dict]:
    out = []
    for dd, mm, yy, d, mes, y, href in _ROW.findall(html):
        out.append({"date": f"20{yy}-{mm}-{dd}",
                    "meeting_date": f"{y}-{MESES[mes.lower()]:02d}-{int(d):02d}",
                    "url": href if href.startswith("http") else BASE + href})
    return out


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
    return sorted(p for p in Path(raw_folder).glob("*.md")
                  if not (Path(extracted_folder) / f"{p.stem}.json").exists())
```

- [ ] **Step 4: Rodar e ver passar**

Run: `python -m pytest tests/test_coleta.py -q`
Expected: 3 passed

- [ ] **Step 5: Escrever `scripts/coletar_banxico.py`**

```python
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


def _get(url: str) -> bytes:
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read()


def _write(doc_type, date, meeting_date, url, text) -> None:
    dest = config.raw_dir("banxico") / f"{colegiado_id(doc_type, date, meeting_date)}.md"
    if dest.exists():
        return
    if len(text.strip()) < MIN_CHARS:
        print(f"ERRO texto ilegível ou curto ({len(text.strip())} chars): {doc_type} {meeting_date} {url}")
        return
    dest.write_text(raw_header(doc_type, date, meeting_date, url) + "\n" + text.strip() + "\n", encoding="utf-8")
    print(f"novo {dest.name} ({doc_type} {meeting_date})")


def comunicados() -> None:
    index = json.loads((HIST / "_index.json").read_text(encoding="utf-8"))
    for e in sorted(index, key=lambda e: e["fecha"]):
        if e["fecha"] < config.START_DATE:
            continue
        txt = HIST / f"{e['fecha']}.txt"
        _write("comunicado", e["fecha"], e["fecha"], e["url"],
               txt.read_text(encoding="utf-8") if txt.exists() else "")


def minutas() -> None:
    for m in parse_minutas(_get(MINUTAS).decode("latin-1")):
        if m["meeting_date"] < config.START_DATE:
            continue
        if (config.raw_dir("banxico") / f"{colegiado_id('ata', m['date'], m['meeting_date'])}.md").exists():
            continue
        with fitz.open(stream=_get(m["url"]), filetype="pdf") as doc:
            text = "\n".join(page.get_text() for page in doc)
        _write("ata", m["date"], m["meeting_date"], m["url"], text)


if __name__ == "__main__":
    config.raw_dir("banxico").mkdir(parents=True, exist_ok=True)
    comunicados()
    minutas()
    for p in pendentes(config.raw_dir("banxico"), config.extracted_dir("banxico")):
        print(f"PENDENTE {p.name}")
```

Nota: o `_index.json` só é atualizado pelo coletor de comunicados que já existe em `Mexico\...\Comunicados`. Se um comunicado novo não aparecer, rode esse coletor primeiro (ou confira se `<fecha>.txt` existe no `_historico`).

- [ ] **Step 6: Rodar a coleta de verdade e conferir**

Run: `python scripts/coletar_banxico.py`
Expected: ~14 linhas `novo ... (comunicado ...)` (2025-02-06 … 2026-09-24), ~13 `novo ... (ata ...)` (a ata de 2026-09-24 só sai ~08/10/2026, então pode não aparecer), nenhuma `ERRO`, e as mesmas ~27 linhas `PENDENTE`. Rode de novo: nenhuma linha `novo` (idempotência). Abra um raw de ata e confira que o texto é a minuta (não página em branco).

- [ ] **Step 7: Commit**

```powershell
git add emrf/coleta_banxico.py scripts/coletar_banxico.py tests/test_coleta.py data/banxico/raw
git commit -m "feat: coleta Banxico (comunicados do _historico, minutas do site) desde 2025`n`nCo-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: Contrato do classificador e classificação da carga inicial

**Files:**
- Create: `agents/10_classificar_colegiado.md`, `scripts/classificar.py`
- Output: `data/banxico/extracted/*.json` (~27)

**Interfaces:**
- Consumes: raw com cabeçalho de `raw_header` (Task 4); `registry/rubric.json`; `load_records` (Task 1) para validar
- Produces: um JSON válido por raw, nome = `speech_id` do cabeçalho

- [ ] **Step 1: Escrever `agents/10_classificar_colegiado.md`**

````markdown
# Agente 10 — classificar um documento colegiado (comunicado ou ata)

**Objetivo:** ler UM documento colegiado de um BC e gravar
`data/<bc>/extracted/<speech_id>.json` com a postura da **Junta como colegiado**
na rubrica `registry/rubric.json`.

**Ferramentas:** Read, Write, Bash (só para rodar o validador).

**Entradas**
- O raw indicado: `data/<bc>/raw/<speech_id>.md`. O cabeçalho `<!-- chave: valor -->`
  traz `speech_id`, `bc`, `doc_type`, `date`, `meeting_date`, `url`. Copie esses valores
  exatamente.
- `registry/rubric.json` — leia inteira.
- `C:\Users\mrabelo\.claude\skills\bc-hawk-dove\references\calibracao.md` — régua da escala.
- O JSON colegiado anterior do mesmo `doc_type` em `data/<bc>/extracted/` (maior `date`
  menor que a deste), se existir — só para descrever o que mudou no `summary`, nunca
  para puxar a nota.

**Unidade de análise.** A mensagem da Junta neste documento: decisão, guidance, balanço
de riscos, votos e divergências. Na **ata**, pondere a discussão ("la mayoría",
"algunos", "uno") — uma ata que revela maioria mais dividida ou mais preocupada com
inflação que o comunicado pontua diferente dele. Não copie a nota do comunicado.

**Régua para comunicados do Banxico** (calibração inicial do piloto, 2026; use como
ordem de grandeza, reavalie pelo texto):
- corte com porta aberta para mais cortes, maioria dividida: **−1.5**
- corte sinalizado como último / pausa à frente: **−0.5**
- manutenção neutra, dependente de dados: **0**
- manutenção com balanço de riscos inclinado para cima e ênfase em inflação: **+0.5**
- alta ou viés explícito de alta: **+2 ou mais**

**Saída — `data/<bc>/extracted/<speech_id>.json`:**
```json
{
  "speech_id": "<do cabeçalho>",
  "bc": "banxico",
  "track": "colegiado",
  "doc_type": "comunicado | ata",
  "member_id": "board",
  "title": "Comunicado <meeting_date> | Minuta <meeting_date>",
  "date": "<do cabeçalho>",
  "meeting_date": "<do cabeçalho>",
  "url": "<do cabeçalho>",
  "source": "banxico",
  "non_policy": false,
  "decision": {"action": "cut|hold|hike", "rate": "6.50%", "vote": "4-1", "dissents": ["Heath (hold)"]},
  "summary": "Um parágrafo em inglês, 3-5 frases: a mensagem de política e o que mudou vs o documento anterior do mesmo tipo.",
  "key_quotes": [{"quote": "verbatim em espanhol", "context": "...", "dimension": "<id>"}],
  "llm_scores": {
    "composite_hawk_dove": 0, "mandate_weight": 0, "inflation_conviction": 0,
    "labor_concern": 0, "policy_stance_read": 0,
    "near_term_bias": {"direction": "hold", "pace": "data-dependent"},
    "theme_flags": []
  },
  "drivers": {"supply_shocks": {"intensity": 0, "push": "neutral"}, "underlying_inflation": {...},
              "fx_external": {...}, "labor_market": {...}, "growth_demand": {...}, "other": {...}},
  "extractor_model": "<modelo desta sessão>", "extracted_at": "<AAAA-MM-DDT00:00:00Z>",
  "rubric_version": "1.0-generic"
}
```

**Regras**
- `title` é EXATAMENTE `Comunicado <meeting_date>` ou `Minuta <meeting_date>` (o `speech_id` depende dele).
- `decision`: extraia do texto. Na ata, é a decisão da reunião a que ela se refere. `dissents`
  lista `"<Sobrenome> (<o que preferia>)"`; `[]` se unânime. `vote` como `"5-0"`, `"4-1"`.
- Scores inteiros ou .5; `null` se o documento não trata da dimensão.
- 2 a 4 `key_quotes` VERBATIM do raw (o validador confere).
- Os seis drivers, todos, sempre.

**Validação obrigatória (tem que imprimir `OK`):**
```
python C:\Users\mrabelo\.claude\skills\bc-hawk-dove\scripts\bc_base.py validar data/<bc>/extracted/<speech_id>.json --rubrica registry/rubric.json --texto data/<bc>/raw/<speech_id>.md
```
Se der erro, corrija o JSON e valide de novo. Não faça mais nada além de gravar esse arquivo.
````

- [ ] **Step 2: Escrever `scripts/classificar.py`**

```python
"""Classifica os raws pendentes com `claude -p`, um documento por chamada.

Sequencial de propósito (no máximo 2 processos claude -p ao mesmo tempo é o teto
medido no bc_comunicacao; aqui usamos 1). Retomar = rodar de novo: só pega quem
ainda não tem JSON.
"""
import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from emrf import config  # noqa: E402
from emrf.coleta_banxico import pendentes  # noqa: E402

PROMPT = ("Classifique o documento colegiado em {raw}. Siga EXATAMENTE agents/10_classificar_colegiado.md "
          "(leia-o primeiro) e grave {out}. Valide com o comando do contrato até imprimir OK. "
          "Não faça mais nada.")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--bc", default="banxico")
    ap.add_argument("--limite", type=int, default=0, help="classificar no máximo N (0 = todos)")
    a = ap.parse_args()
    todo = pendentes(config.raw_dir(a.bc), config.extracted_dir(a.bc))
    if a.limite:
        todo = todo[:a.limite]
    falhas = []
    for raw in todo:
        out = config.extracted_dir(a.bc) / f"{raw.stem}.json"
        print(f"== {raw.name}", flush=True)
        subprocess.run(["claude", "-p", PROMPT.format(raw=raw.relative_to(config.ROOT).as_posix(),
                                                      out=out.relative_to(config.ROOT).as_posix()),
                        "--permission-mode", "acceptEdits", "--allowedTools", "Read,Write,Bash"],
                       cwd=config.ROOT, check=False, shell=sys.platform == "win32")
        if not out.exists():
            falhas.append(raw.name)
    print(f"classificados {len(todo) - len(falhas)}/{len(todo)}")
    for f in falhas:
        print(f"FALHOU {f}")
    sys.exit(1 if falhas else 0)
```

- [ ] **Step 3: Classificar 2 documentos e inspecionar antes da carga toda**

Run: `python scripts/classificar.py --limite 2`
Expected: `classificados 2/2`. Abra os dois JSON: `title` canônico, `decision` coerente com o texto, quotes em espanhol, composto na régua. Rode `python -m pytest -q` e `python scripts/build.py` (tem que imprimir `OK`). Se o contrato precisar de ajuste, corrija o `.md`, apague só esses JSON de `extracted/` e repita.

- [ ] **Step 4: Classificar o resto**

Run: `python scripts/classificar.py`
Expected: `classificados N/N`, sem `FALHOU`. Se houver falha, rode de novo (retoma só as pendentes). Depois: `python scripts/build.py` → `OK`.

- [ ] **Step 5: Conferência de sanidade da série (mostrar ao analista)**

```powershell
python -c "import sys; sys.path.insert(0,'.'); from emrf.schema import load_records; from emrf.board import board_series; [print(p['date'], p['doc_type'].ljust(10), p['level']) for p in board_series(load_records('banxico'))]"
```
Expected: ~27 linhas em ordem de data. Compare os 5 comunicados de 2026 com o piloto (`hawk_dove_rubrica/scores_banxico.csv`: −1.5, −0.5, 0, +0.5, −0.5). Diferenças > 1 ponto: reportar ao analista com o motivo, não corrigir por conta própria.

- [ ] **Step 6: Commit**

```powershell
git add agents/10_classificar_colegiado.md scripts/classificar.py data/banxico/extracted
git commit -m "data: comunicados e atas do Banxico desde 2025 classificados`n`nCo-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 6: Publicação no GitHub Pages

**Files:**
- Create: `CLAUDE.md`
- Git: `index.html` (blob de `results/index.html`)

**Interfaces:**
- Consumes: `scripts/build.py` (Task 3), dados (Task 5)
- Produces: site em `https://mrabelosouza-maker.github.io/em-reaction-functions/`

- [ ] **Step 1: Pedir ao analista que crie o repositório (sem `gh` nesta máquina)**

Pare e peça: criar no GitHub, conta `mrabelosouza-maker`, um repositório **público** vazio `em-reaction-functions` (sem README), e confirmar. Não prossiga sem a confirmação.

- [ ] **Step 2: Escrever `CLAUDE.md`**

```markdown
# CLAUDE.md — EM Reaction Functions

Site (GitHub Pages) com a escala hawk-dove de BCs emergentes: trilha colegiada
(comunicado, ata) e trilha de membros (falas, calls privados). v1: Banxico desde 2025.
Spec: docs/superpowers/specs/2026-09-28-em-reaction-functions-design.md.

## Costura
agentes (`claude -p`, skill bc-hawk-dove) -> data/<bc>/extracted/<speech_id>.json -> emrf/ -> results/index.html
`emrf/` nunca chama modelo nem rede. Remontar é grátis: `python scripts/build.py`.

## Rotinas
- **Atualizar o Banxico** (após decisão ou ata): `python scripts/coletar_banxico.py`
  -> `python scripts/classificar.py` -> `python -m pytest -q` -> `python scripts/build.py` -> publicar.
- **Membro (fala/call):** skill `bc-hawk-dove`; grava em data/<bc>/raw e extracted com
  `track=membro`, `doc_type` fala_publica|call_privado, `bc`; `member_id` tem que estar em
  registry/<bc>/roster.json. Depois build + publicar.

## Publicar
```powershell
python scripts/build.py
$blob = git hash-object -w results/index.html
git update-index --add --cacheinfo "100644,$blob,index.html"
git add <arquivos de dados novos>
git commit -m "<mensagem>"
git cat-file -s HEAD:index.html   # tem que bater com o tamanho de results/index.html
git push origin main
```
Nunca `git add index.html` do working tree (o share R: trunca arquivos grandes).
Nunca `git add -A`/`git add .`.

## Decisões (não repropor sem o analista)
- Tudo público, inclusive calls privados.
- Board = degrau único atualizado por comunicado OU ata (risco de gênero declarado na Metodologia).
- Colegiado: `member_id=board`, título canônico `Comunicado|Minuta <meeting_date>`.
- Rubrica 1.0-generic da skill; drivers gravados mas sem visualização na v1.
- Fora da v1: RTI, outros BCs, backfill de calls do Notion (Vault/raw/calls/MX), pré-2025,
  convergência com Modelagem/bc_comunicacao (Chile).
- Nunca editar/apagar raw gravado.
```

- [ ] **Step 3: Publicar**

```powershell
python -m pytest -q
python scripts/build.py
git remote add origin https://github.com/mrabelosouza-maker/em-reaction-functions.git
$blob = git hash-object -w results/index.html
git update-index --add --cacheinfo "100644,$blob,index.html"
git add CLAUDE.md
git commit -m "site: primeira publicacao (Banxico, comunicados e atas desde 2025)`n`nCo-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
git cat-file -s HEAD:index.html
(Get-Item results/index.html).Length
git branch -M main
git push -u origin main
```
Expected: os dois tamanhos iguais; push OK.

- [ ] **Step 4: Ativar o Pages e conferir**

Peça ao analista: Settings → Pages → Source "Deploy from a branch", `main`, `/ (root)`. Depois abra `https://mrabelosouza-maker.github.io/em-reaction-functions/` (WebFetch) e confira: aba Banxico e Metodologia presentes, KPIs preenchidos, ~27 documentos na base.

---

### Task 7: Ligar a skill `bc-hawk-dove` a esta base

**Files:**
- Modify: `C:\Users\mrabelo\.claude\skills\bc-hawk-dove\references\bancos.md` (acrescentar seção antes de "## Padrão para os demais BCs")
- Modify: `C:\Users\mrabelo\.claude\skills\bc-hawk-dove\SKILL.md` (passo 4, bloco de schema: acrescentar campos)

- [ ] **Step 1: Acrescentar a seção do Banxico em `bancos.md`**

```markdown
## Banxico — base com site (em_reaction_functions)

| Item | Valor |
|---|---|
| Repositório | `R:\Macro EMs\Modelagem\em_reaction_functions` (ler o `CLAUDE.md` de lá) |
| Rubrica | `registry/rubric.json` do repo (= `references/rubrica.json`, 1.0-generic) |
| Texto bruto | `data/banxico/raw/<speech_id>.md` |
| Classificação | `data/banxico/extracted/<speech_id>.json` |
| Membros | `registry/banxico/roster.json` (`member_id` tem que estar lá; o build rejeita o resto) |
| Campos extras obrigatórios | `"bc": "banxico"`, `"track": "membro"`, `"doc_type": "fala_publica"` ou `"call_privado"` |
| Call privado | `doc_type=call_privado`, `source="notas próprias"`, `url` = home do Banxico. Vai a público (decisão do analista). |
| Anterior | `bc_base.py anterior data/banxico/extracted <member_id> --antes <data>` |
| Publicar | seção "Publicar" do `CLAUDE.md` do repo (build + blob + push) |

Os documentos colegiados (comunicado, ata) **não** passam por esta skill: são do
pipeline do repo (`scripts/coletar_banxico.py` + `scripts/classificar.py`).
```

- [ ] **Step 2: No `SKILL.md`, passo 4, acrescentar ao bloco de schema e à lista de princípios**

No JSON de exemplo do passo 4, depois de `"speech_id": "...", "member_id": "...",` acrescente a linha:
```
  "bc": "<slug, só em bases com site EM>", "track": "membro", "doc_type": "fala_publica|call_privado",
```
E na seção "### 5. Publicar", troque a primeira frase por:
```
Fed: siga `<skill>/references/fed.md` à risca. Banxico (e demais BCs em `em_reaction_functions`): siga a seção "Publicar" do `CLAUDE.md` daquele repo.
```

- [ ] **Step 3: Testar ponta a ponta com uma fala real**

Peça ao analista uma fala ou call recente de um membro do Banxico (ou use uma matéria pública recente). Rode a skill em modo completo. Conferir: JSON validado pela skill, `python -m pytest -q` e `python scripts/build.py` OK, o ponto do membro aparece no gráfico Board+membros, no heatmap e no card, e o push saiu. **Antes do push, confirme com o analista** que aquele registro pode ir a público.

- [ ] **Step 4: Commit no repo (dados do teste)**

O commit/push dos dados segue a seção Publicar do `CLAUDE.md`. As mudanças da skill ficam fora do git (a pasta da skill não é repositório).

---

## Self-review

- Spec §2 escopo → Tasks 4–5 (só comunicado/ata desde 2025). §3 decisões → Global Constraints + CLAUDE.md. §4 arquitetura → Tasks 1–3. §5 contrato → Task 1 (divergência: `speech_id` na fórmula da skill em vez de `<bc>-<member>-<doc_type>-YYYYMMDD`, para a skill `validar`/`anterior` funcionarem sem mudança; e sem `calendar.json`). §6 série/desvio → Task 2. §7 páginas → Task 3. §8 fluxos → Tasks 4, 5, 7. §9 erros/verificação → validação estrita (Task 1), `ERRO` na coleta (Task 4), smoke test (Task 3), conferência do site (Task 6).
- Nomes cruzados conferidos: `colegiado_id/colegiado_title` (T1→T4, T5), `board_*`/`member_points`/`heatmap`/`kpis`/`member_cards` (T2→T3), `pendentes` (T4→T5), `load_records(bc, folder)` (T1→T3, T5).
````
