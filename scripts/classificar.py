"""Classifica os raws pendentes com `claude -p`, um documento por chamada.

Sequencial de propósito (no máximo 2 processos claude -p ao mesmo tempo é o teto
medido no bc_comunicacao; aqui usamos 1). Retomar = rodar de novo: só pega quem
ainda não tem JSON.
"""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from emrf import config  # noqa: E402
from emrf.coleta_banxico import pendentes  # noqa: E402

PROMPT = ("Classifique o documento colegiado em {raw}. Siga EXATAMENTE agents/10_classificar_colegiado.md "
          "(leia-o primeiro) e grave {out}. Valide com o comando do contrato até imprimir OK. "
          "Não faça mais nada.")

def claude_bin():
    """No Windows, `claude` e um .cmd; cmd.exe nao aceita cwd UNC, entao chama o .exe direto."""
    exe = shutil.which("claude") or "claude"
    exe_nativo = Path(exe).parent / "node_modules" / "@anthropic-ai" / "claude-code" / "bin" / "claude.exe"
    return str(exe_nativo) if exe_nativo.exists() else exe


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
        subprocess.run([claude_bin(), "-p", PROMPT.format(raw=raw.relative_to(config.ROOT).as_posix(),
                                                      out=out.relative_to(config.ROOT).as_posix()),
                        "--permission-mode", "acceptEdits", "--allowedTools", "Read,Write,Bash"],
                       cwd=config.ROOT, check=False)
        if not out.exists():
            falhas.append(raw.name)
    print(f"classificados {len(todo) - len(falhas)}/{len(todo)}")
    for f in falhas:
        print(f"FALHOU {f}")
    sys.exit(1 if falhas else 0)
