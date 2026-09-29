"""Classifica os raws pendentes com `claude -p`, um documento por chamada.

Sequencial de propósito (no máximo 2 processos claude -p ao mesmo tempo é o teto
medido no bc_comunicacao; aqui usamos 1). Retomar = rodar de novo: só pega quem
ainda não tem JSON.
"""
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from emrf import config  # noqa: E402
from emrf.schema import Record  # noqa: E402
from emrf.coleta_banxico import pendentes  # noqa: E402

PROMPT = ("Classifique o documento colegiado em {raw}. Siga EXATAMENTE agents/10_classificar_colegiado.md "
          "(leia-o primeiro) e grave {out}. Valide com o comando do contrato até imprimir OK. "
          "Não faça mais nada.")


def claude_bin():
    """No Windows, `claude` e um .cmd; cmd.exe nao aceita cwd UNC, entao chama o .exe direto."""
    exe = shutil.which("claude") or "claude"
    exe_nativo = Path(exe).parent / "node_modules" / "@anthropic-ai" / "claude-code" / "bin" / "claude.exe"
    return str(exe_nativo) if exe_nativo.exists() else exe


def verificar(out: Path, stem: str) -> str | None:
    """None se `out` existe e valida (schema + speech_id == stem); senao a mensagem de erro.
    JSON invalido e renomeado para `.json.invalido` (pendentes o retenta; a saida fica para inspecao)."""
    if not out.exists():
        return "JSON nao gerado"
    try:
        rec = Record.from_json(json.loads(out.read_text(encoding="utf-8"))).validate()
        if rec.speech_id != stem:
            raise ValueError(f"speech_id {rec.speech_id!r} != {stem!r}")
    except Exception as e:  # noqa: BLE001 - qualquer falha de parse/schema invalida a saida
        out.replace(out.with_name(out.name + ".invalido"))
        return f"{type(e).__name__}: {e}"
    return None


def _cauda(txt: str | None, n: int = 20) -> str:
    return chr(10).join((txt or "").splitlines()[-n:])


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--bc", default="banxico")
    ap.add_argument("--limite", type=int, default=0, help="classificar no máximo N (0 = todos)")
    a = ap.parse_args()
    todo = pendentes(config.raw_dir(a.bc), config.extracted_dir(a.bc))
    if a.limite:
        todo = todo[:a.limite]
    claude = claude_bin()
    falhas = []
    for raw in todo:
        out = config.extracted_dir(a.bc) / f"{raw.stem}.json"
        print(f"== {raw.name}", flush=True)
        cmd = [claude, "-p", PROMPT.format(raw=raw.relative_to(config.ROOT).as_posix(),
                                           out=out.relative_to(config.ROOT).as_posix()),
               "--permission-mode", "acceptEdits", "--allowedTools", "Read,Write,Bash(python:*)"]
        try:
            r = subprocess.run(cmd, cwd=config.ROOT, check=False, timeout=900, capture_output=True,
                               text=True, encoding="utf-8", errors="replace")
        except subprocess.TimeoutExpired:
            print(f"TIMEOUT {raw.name}")
            falhas.append(raw.name)
            continue
        print(r.stdout)
        erro = f"returncode {r.returncode}" if r.returncode else verificar(out, raw.stem)
        if erro:
            if out.with_name(out.name + ".invalido").exists():
                print(f"INVALIDO {out.name}: {erro}")
            print(f"returncode {r.returncode}")
            print("--- stderr ---", _cauda(r.stderr), "--- stdout ---", _cauda(r.stdout), sep=chr(10))
            falhas.append(raw.name)
    print(f"classificados {len(todo) - len(falhas)}/{len(todo)}")
    for f in falhas:
        print(f"FALHOU {f}")
    sys.exit(1 if falhas else 0)
