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
