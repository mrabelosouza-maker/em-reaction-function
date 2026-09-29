import importlib.util
import json
from pathlib import Path

import pytest

_spec = importlib.util.spec_from_file_location(
    "classificar", Path(__file__).resolve().parents[1] / "scripts" / "classificar.py")
classificar = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(classificar)


def _grava(tmp_path, d):
    out = tmp_path / f"{d['speech_id']}.json"
    out.write_text(json.dumps(d), encoding="utf-8")
    return out


def test_valido(tmp_path, make_record):
    d = make_record()
    assert classificar.verificar(_grava(tmp_path, d), d["speech_id"]) is None


def test_ausente(tmp_path):
    assert classificar.verificar(tmp_path / "x.json", "x")


def test_invalido_renomeia(tmp_path, make_record):
    d = make_record(composite=9)
    out = _grava(tmp_path, d)
    assert classificar.verificar(out, d["speech_id"])
    assert not out.exists()
    assert out.with_name(out.name + ".invalido").exists()


def test_speech_id_diferente_do_stem(tmp_path, make_record):
    d = make_record()
    out = _grava(tmp_path, d)
    assert classificar.verificar(out, "outro-stem")
    assert out.with_name(out.name + ".invalido").exists()
