"""
Tidy the prose in notebooks and source files.

    python tools/tidy_prose.py --check    report only, change nothing
    python tools/tidy_prose.py            apply

Two passes, both text-only. Executable code is never touched:

  1. Em dashes are replaced with ordinary punctuation. Paired dashes become
     parentheses, a dash before a relative clause becomes a comma, and a dash
     before an explanation becomes a colon.
  2. Verbose passages listed in CONDENSE are swapped for shorter wording that
     keeps the same claim.

Run it after editing prose, then re-run tools/run_notebooks.py so the stored
outputs still match the cells above them.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EM = "\u2014"

# Words that start a relative or coordinating clause. A dash in front of one of
# these is nearly always doing a comma's job.
CLAUSE_STARTERS = (
    "which", "who", "whom", "whose", "and", "but", "so", "yet", "or", "nor",
    "then", "not", "against", "same", "no", "one", "two", "three", "four",
    "five", "six", "22", "230", "395", "1.4", "+1.4", "-3.5",
)


def fix_em_dashes(text: str) -> str:
    """Replace em dashes with ordinary punctuation, line by line."""
    out = []
    for line in text.split("\n"):
        if EM not in line:
            out.append(line)
            continue

        # Markdown table cell used as an empty placeholder.
        line = re.sub(r"\|\s*" + EM + r"\s*\|", "| n/a |", line)
        line = re.sub(r"\|\s*" + EM + r"\s*$", "| n/a", line)

        # Paired dashes inside one line become a parenthetical.
        line = re.sub(
            r" " + EM + r" ([^" + EM + r"]{3,80}?) " + EM + r" ",
            r" (\1) ",
            line,
        )

        # Remaining single dashes.
        def one(match: re.Match) -> str:
            after = match.group(1)
            first = after.split()[0].strip("*`\"'").lower() if after.split() else ""
            if first in CLAUSE_STARTERS:
                return ", " + after
            # An explanation of what came before reads as a colon.
            return ": " + after

        line = re.sub(r" " + EM + r" (\S.*)$", one, line)
        # A dash still left is unspaced or line-final; a comma is safe there.
        line = line.replace(EM, ",")
        out.append(line)
    return "\n".join(out)


# Verbose passage -> shorter wording. Keyed on an exact substring so a failed
# match is reported rather than silently skipped.
CONDENSE: list[tuple[str, str]] = [
    # --- 00_setup ---
    (
        "Everything heavy happens once, in `01`. The rest load parquet in under a\n"
        "second, so you can iterate on an angle without re-running the ETL.",
        "`01` does the heavy work once. The rest load parquet in under a second.",
    ),
    (
        "If a cell here grows past ~20 lines and has no output\n"
        "worth looking at, it belongs in `etl.py`.",
        "A cell over ~20 lines with no output worth reading belongs in `etl.py`.",
    ),
    (
        "All resolved from `src/nbinit.py`, so they hold regardless of the kernel's\n"
        "working directory.",
        "Resolved in `src/nbinit.py`, so they hold whatever the kernel's working\n"
        "directory is.",
    ),
    # --- 01_ingest_clean ---
    (
        "Four raw CSVs in, seven cached parquet frames out. This is the only notebook\n"
        "that touches the zip; everything downstream reads `clean/`.",
        "Four raw CSVs in, seven parquet frames out. The only notebook that touches\n"
        "the zip; everything downstream reads `clean/`.",
    ),
    (
        "Column names are lowercased and snake_cased on the way in. Nothing else is\n"
        "touched yet",
        "Column names are lowercased and snake_cased on the way in. Nothing else is\n"
        "changed yet",
    ),
    (
        "Everything arrives as `object` from CSV. `etl.clean_all` applies a per-table\n"
        "spec: dates tried ISO-first then day-first (the HRIS exports mix both),\n"
        "booleans from the seven spellings of \"true\" in the wild, and numerics with\n"
        "currency symbols and thousands separators stripped.",
        "CSV gives everything as `object`. `etl.clean_all` applies a per-table spec:\n"
        "dates ISO first then day-first (the exports mix both), booleans from the\n"
        "several spellings of \"true\", numerics with currency symbols stripped.",
    ),
    (
        "`to_date` coerces failures to `NaT`, so a silent format problem would show up\n"
        "here as a jump in nulls rather than an exception.",
        "`to_date` coerces failures to `NaT`, so a format problem shows up as a jump\n"
        "in nulls rather than an exception.",
    ),
    (
        "Parquet keeps the dtypes (nullable booleans, categoricals, datetimes) that\n"
        "CSV would flatten back to strings, and reloads in well under a second.",
        "Parquet keeps the dtypes CSV would flatten to strings, and reloads in under\n"
        "a second.",
    ),
    (
        "Reading back what we just wrote, so a dtype that parquet cannot represent\n"
        "fails here rather than three notebooks downstream.",
        "Read back what was just written, so an unrepresentable dtype fails here\n"
        "rather than three notebooks downstream.",
    ),
    # --- 02_data_quality ---
    (
        "Written to `clean/data_quality.csv` so the DQ slide can be rebuilt from a\n"
        "file rather than a screenshot.",
        "Written to `clean/data_quality.csv` so the DQ slide rebuilds from a file,\n"
        "not a screenshot.",
    ),
    (
        "Every null in this dataset is explainable, which is itself worth saying out\n"
        "loud: it means missingness is not the story here.",
        "Every null here is explainable, which is worth stating: missingness is not\n"
        "the story.",
    ),
    (
        "This governs what the comparison can support, so it goes before the charts\n"
        "rather than in a footnote.",
        "This governs what the comparison can support, so it goes before the charts.",
    ),
    # --- 03_angle1_cost ---
    (
        "The method is deliberately blunt: take Finance's *own* unit costs, divide the\n"
        "published range by them to get an implied population, and compare against the\n"
        "observed one. No new assumptions, so the gap cannot be argued away as a\n"
        "modelling choice.",
        "The method is blunt on purpose: take Finance's own unit costs, divide the\n"
        "published range by them for an implied population, compare with the observed\n"
        "one. No new assumptions, so the gap is not a modelling choice.",
    ),
    (
        "Two thresholds were chosen by us, not by the brief: the disengagement score\n"
        "cut-off (3.0) and how many low waves count as *persistent* (2). If the\n"
        "headline flips under a reasonable alternative, it is not a finding.",
        "Two thresholds are ours, not the brief's: the score cut-off (3.0) and how\n"
        "many low waves count as persistent (2). If the headline flips under a\n"
        "reasonable alternative, it is not a finding.",
    ),
    (
        "A total is not actionable. This is the cut that turns the number into a\n"
        "recommendation.",
        "A total is not actionable. This cut turns the number into a recommendation.",
    ),
    # --- 04_angle2_far ---
    (
        "`etl.FAR_WAVE_MAP` assigns each department to a wave. It was written from the\n"
        "brief, before anyone had seen the department values. Check it first: an\n"
        "unmapped department silently becomes an `Unmapped` bucket that quietly drops\n"
        "out of every comparison.",
        "`etl.FAR_WAVE_MAP` assigns each department to a wave, written from the brief\n"
        "before anyone saw the department values. Check it first: an unmapped\n"
        "department becomes an `Unmapped` bucket that drops out of every comparison.",
    ),
    (
        "A rise in exits after March 2024 could just be a rise in exits. The test that\n"
        "isolates FAR is whether the rise is **larger for regulated roles than for\n"
        "their unregulated colleagues in the same wave**, same company, same market,\n"
        "same twelve months.",
        "A rise in exits after March 2024 could just be a rise in exits. The test that\n"
        "isolates FAR is whether the rise is **larger for regulated roles than for\n"
        "unregulated colleagues in the same wave**: same company, market and months.",
    ),
    # --- 05_angle3_silence ---
    (
        "The appeal is operational: a score needs a survey cycle and an analyst.\n"
        "Non-response is known the day the wave closes, needs no model, and applies to\n"
        "the people nobody currently has data on.",
        "The appeal is operational. A score needs a survey cycle and an analyst;\n"
        "non-response is known the day the wave closes, needs no model, and covers the\n"
        "people nobody has data on.",
    ),
    (
        "A predictor is only useful if it fires before you could have guessed anyway.\n"
        "For everyone who left, line their survey waves up against their exit date and\n"
        "ask when they stopped answering.",
        "A predictor is only useful if it fires before you could have guessed. For\n"
        "everyone who left, line their waves up against their exit date and ask when\n"
        "they stopped answering.",
    ),
    (
        "The operational case, at Finance's own replacement cost. Deliberately\n"
        "conservative: it assumes an intervention reaches only the silent employees\n"
        "who were going to leave, and works on a fraction of them.",
        "The operational case at Finance's replacement cost, deliberately\n"
        "conservative: an intervention reaches only the silent employees who were\n"
        "going to leave, and works on a fraction of them.",
    ),
]


def apply_condense(text: str, hits: set[int]) -> str:
    for i, (old, new) in enumerate(CONDENSE):
        if old in text:
            text = text.replace(old, new)
            hits.add(i)
    return text


def tidy_notebook(path: Path, hits: set[int]) -> tuple[int, int]:
    nb = json.loads(path.read_text(encoding="utf-8"))
    dashes = shortened = 0

    for cell in nb["cells"]:
        src = "".join(cell["source"])
        original = src

        if cell["cell_type"] == "markdown":
            dashes += src.count(EM)
            src = fix_em_dashes(src)
            before = src
            src = apply_condense(src, hits)
            if src != before:
                shortened += 1
        else:
            # Code cells: only comments and the text inside plot labels carry
            # dashes, and both are prose. Logic is untouched either way.
            dashes += src.count(EM)
            src = fix_em_dashes(src)

        if src != original:
            cell["source"] = src.splitlines(keepends=True)

    path.write_text(json.dumps(nb, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return dashes, shortened


def tidy_python(path: Path) -> int:
    text = path.read_text(encoding="utf-8")
    count = text.count(EM)
    if count:
        path.write_text(fix_em_dashes(text), encoding="utf-8")
    return count


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="report only, write nothing")
    args = ap.parse_args()

    if args.check:
        total = 0
        for path in sorted(ROOT.glob("notebooks/*.ipynb")) + sorted(ROOT.glob("src/*.py")):
            n = path.read_text(encoding="utf-8").count(EM)
            if n:
                print(f"  {path.relative_to(ROOT)}: {n} em dashes")
            total += n
        print(f"\n  {total} em dashes across the repo")
        return 1 if total else 0

    hits: set[int] = set()
    print("  notebooks")
    for path in sorted(ROOT.glob("notebooks/*.ipynb")):
        dashes, shortened = tidy_notebook(path, hits)
        print(f"    {path.name:26} {dashes:>3} dashes  {shortened:>2} passages shortened")

    print("  source")
    for path in sorted(ROOT.glob("src/*.py")) + sorted(ROOT.glob("tools/*.py")):
        if path.name == "tidy_prose.py":
            continue
        n = tidy_python(path)
        if n:
            print(f"    {path.name:26} {n:>3} dashes")

    missed = [i for i in range(len(CONDENSE)) if i not in hits]
    if missed:
        print(f"\n  {len(missed)} CONDENSE entries did not match (index {missed}).")
        print("  The wording changed; update the entry or drop it.")

    print("\n  Re-run tools/run_notebooks.py so stored outputs match the edited cells.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
