"""
Execute the notebooks in order, in place.

    python tools/run_notebooks.py                # all of them
    python tools/run_notebooks.py 02 04          # only those, by number prefix

Useful for two things: proving the whole chain still runs after an `etl.py`
change, and refreshing every figure before a deck deadline without clicking
through six notebooks. Outputs are written back into the .ipynb, so what you
open afterwards is what ran.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import nbformat
from nbclient import NotebookClient
from nbclient.exceptions import CellExecutionError

ROOT = Path(__file__).resolve().parent.parent
NOTEBOOKS = ROOT / "notebooks"
TIMEOUT = 600


def run(path: Path) -> bool:
    nb = nbformat.read(path, as_version=4)
    client = NotebookClient(
        nb,
        timeout=TIMEOUT,
        kernel_name="python3",
        resources={"metadata": {"path": str(path.parent)}},
    )

    started = time.perf_counter()
    try:
        client.execute()
        ok, detail = True, ""
    except CellExecutionError as exc:
        ok = False
        detail = str(exc).strip().splitlines()[-1]
    finally:
        nbformat.write(nb, path)

    elapsed = time.perf_counter() - started
    print(f"  {'PASS' if ok else 'FAIL'}  {path.name:<28} {elapsed:>6.1f}s"
          + (f"\n        {detail}" if detail else ""))
    return ok


def main(argv: list[str]) -> int:
    wanted = argv[1:]
    paths = sorted(NOTEBOOKS.glob("*.ipynb"))
    if wanted:
        paths = [p for p in paths if any(p.name.startswith(w) for w in wanted)]

    if not paths:
        print("  no notebooks matched")
        return 1

    print(f"  executing {len(paths)} notebook(s) from {NOTEBOOKS.relative_to(ROOT)}\n")
    results = [run(p) for p in paths]

    failed = results.count(False)
    print(f"\n  {results.count(True)} passed, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
