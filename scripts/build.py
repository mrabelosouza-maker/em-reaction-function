"""Remonta results/index.html a partir de data/<bc>/extracted/. Grátis e reproduzível."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from emrf.build import build  # noqa: E402

if __name__ == "__main__":
    out = build()
    print(f"OK {out} ({out.stat().st_size} bytes)")
