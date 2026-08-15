"""
Put every component of the Angle 1 cost bridge on the same annual basis.

    python tools/fix_annualisation.py

The bridge compares observed counts against Finance's cost ranges, which are
stated per year. Two of the three observed counts were not annual:

  Regrettable attrition   flow    153 flags across the 24-month window
  Hiring inefficiency     flow    3,243 agency hires across all time, back to 1988
  Disengagement           stock   3,219 people currently disengaged, already annual

This script windows the flows to the observation period, divides by its length,
and leaves the stock alone. It edits src/etl.py, notebooks/03_angle1_cost.ipynb
and dashboard/index.html.

Idempotent. Re-run tools/run_notebooks.py afterwards.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# --------------------------------------------------------------------------
# 1. src/etl.py: name the window length so no cell has to divide by a literal
# --------------------------------------------------------------------------

ETL_OLD = """OBS_START = pd.Timestamp("2024-01-01")
OBS_END = pd.Timestamp("2025-12-31")"""

ETL_NEW = '''OBS_START = pd.Timestamp("2024-01-01")
OBS_END = pd.Timestamp("2025-12-31")

# The window is 24 months. Finance's cost ranges are stated per year, so any
# count of events (exits, hires) has to be divided by this before the two are
# compared. Counts of people in a state (currently disengaged) are already
# annual and must not be divided.
OBS_YEARS = 2.0'''


def patch_etl() -> bool:
    path = ROOT / "src" / "etl.py"
    text = path.read_text(encoding="utf-8")
    if "OBS_YEARS" in text:
        return False
    if ETL_OLD not in text:
        print("  etl.py: OBS_START block not found, skipped")
        return False
    path.write_text(text.replace(ETL_OLD, ETL_NEW), encoding="utf-8")
    return True


# --------------------------------------------------------------------------
# 2. notebooks/03_angle1_cost.ipynb
# --------------------------------------------------------------------------

CELL5_OLD = '''observed = {
    "Regrettable attrition": int(df["regrettable_hr"].sum()),
    "Disengagement": int(df["persistently_disengaged"].fillna(False).sum()),
    "Hiring inefficiency": int(df["hire_source"].eq("agency").sum()),
}'''

CELL5_NEW = '''# Flows are counted inside the observation window, then divided by its length.
# Stocks are not divided. Mixing the two is what produced the earlier $143.7M.
in_window = df["hire_date"].between(etl.OBS_START, etl.OBS_END)

flows = {
    # Exits are already confined to the window by construction.
    "Regrettable attrition": int(df["regrettable_hr"].sum()),
    # Agency hires run back to 1988, so this one has to be windowed.
    "Hiring inefficiency": int((df["hire_source"].eq("agency") & in_window).sum()),
}
stocks = {
    # People currently disengaged. A count of a state, so already per year.
    "Disengagement": int(df["persistently_disengaged"].fillna(False).sum()),
}

observed = {
    "Regrettable attrition": flows["Regrettable attrition"] / etl.OBS_YEARS,
    "Disengagement": stocks["Disengagement"],
    "Hiring inefficiency": flows["Hiring inefficiency"] / etl.OBS_YEARS,
}

print(f"  Agency hires, all time      : {int(df['hire_source'].eq('agency').sum()):,}")
print(f"  Agency hires, in window     : {flows['Hiring inefficiency']:,}")
print(f"  Agency hires, per year      : {observed['Hiring inefficiency']:,.0f}")
print(f"  Regrettable exits, in window: {flows['Regrettable attrition']:,}")
print(f"  Regrettable exits, per year : {observed['Regrettable attrition']:,.0f}")'''

CELL5_TABLE_OLD = '''        "observed_n": observed[label],
        "observed_cost_$m": round(observed[label] * unit[label] / 1e6, 1),'''

CELL5_TABLE_NEW = '''        "observed_n_per_year": round(observed[label]),
        "observed_cost_$m": round(observed[label] * unit[label] / 1e6, 1),'''

CELL5_MULT_OLD = '''bridge["multiple_of_high"] = (bridge["observed_n"] / bridge["implied_n_high"]).round(1)'''
CELL5_MULT_NEW = '''bridge["multiple_of_high"] = (
    bridge["observed_n_per_year"] / bridge["implied_n_high"]).round(1)'''

# Markdown replacements, keyed on an exact substring.
MD_EDITS: list[tuple[str, str]] = [
    (
        "The three counts below are the judgement calls in this notebook, so they are\n"
        "stated plainly rather than buried in a helper:",
        "Finance's ranges are annual, so the observed side has to be annual too. Two\n"
        "of these three are flows and one is a stock, and they are handled differently:",
    ),
    (
        "- **Regrettable attrition**: HR's own `regrettable_flag`. Section 4 revisits\n"
        "  what happens if you use an evidence-based definition instead.",
        "- **Regrettable attrition** is a flow. HR's own `regrettable_flag`, counted\n"
        "  across the 24-month window and divided by two. Section 4 revisits what an\n"
        "  evidence-based definition does to it.",
    ),
    (
        "- **Hiring inefficiency**: employees sourced through an agency.",
        "- **Hiring inefficiency** is a flow. Agency hires *inside the observation\n"
        "  window*, divided by two. The roster carries agency hires back to 1988, so\n"
        "  the unwindowed count of 3,243 is a cumulative headcount, not an annual rate.",
    ),
    (
        "- **Disengagement**: employees with a composite score below 3.0 in two or\n"
        "  more waves they actually answered. Section 5 sensitivity-tests both numbers.",
        "- **Disengagement** is a stock: how many people are in that state, not how\n"
        "  many entered it. Already annual, so it is not divided. Section 5\n"
        "  sensitivity-tests the threshold.",
    ),
    (
        "Regrettable attrition lands **inside** Finance's range: their model is not\n"
        "broken. The other two components are out by multiples, and the reason is the\n"
        "same in both cases: Finance sized them from a rate, and the data has a\n"
        "population.",
        "Two of the three land **below** Finance's range. Only disengagement is out,\n"
        "and it is out by 4.1x. That changes the claim: the $42M is not too small\n"
        "overall, it is pointed at the wrong component.",
    ),
    (
        "The framing for the deck is not \"Finance got it wrong.\" It is: *the $42M\n"
        "counts the departures it can see. It does not count the people who are still\n"
        "here and disengaged, or the premium being paid to replace them.*",
        "The framing for the deck is not \"Finance got it wrong.\" It is: *Finance\n"
        "priced the leavers carefully and the stayers barely at all. The disengaged\n"
        "population is four times the size the model assumes.*",
    ),
]

STORY_OLD = """## The Angle 1 story"""
STORY_NEW = """## The Angle 1 story"""


def patch_notebook() -> tuple[int, int]:
    path = ROOT / "notebooks" / "03_angle1_cost.ipynb"
    nb = json.loads(path.read_text(encoding="utf-8"))
    code_hits = md_hits = 0

    for cell in nb["cells"]:
        src = "".join(cell["source"])
        before = src

        if cell["cell_type"] == "code":
            if CELL5_OLD in src:
                src = src.replace(CELL5_OLD, CELL5_NEW)
            src = src.replace(CELL5_TABLE_OLD, CELL5_TABLE_NEW)
            src = src.replace(CELL5_MULT_OLD, CELL5_MULT_NEW)
            # Department cost table is a 24-month total; say so in its own title.
            src = src.replace(
                '"No single department dominates, the cost is broad, not concentrated"',
                '"No single department dominates, the cost is broad, not concentrated"',
            )
            if src != before:
                code_hits += 1
        else:
            for old, new in MD_EDITS:
                if old in src:
                    src = src.replace(old, new)
                    md_hits += 1

        if src != before:
            cell["source"] = src.splitlines(keepends=True)

    path.write_text(json.dumps(nb, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return code_hits, md_hits


# --------------------------------------------------------------------------
# 3. dashboard/index.html
# --------------------------------------------------------------------------

DASH_EDITS: list[tuple[str, str]] = [
    (
        "Apply <strong>Finance's own unit costs</strong>, unchanged, straight from the brief, to the population actually present in the data, and the figure lands at <strong>$143.7M</strong>. Nothing was re-derived and no new assumption was introduced. The gap is entirely a headcount question: Finance costed roughly the right number of regrettable exits and roughly a fifth of the disengaged and agency-hired staff who are sitting in the file.",
        "Apply <strong>Finance's own unit costs</strong>, unchanged, straight from the brief, to the population actually present in the data, and the figure lands at <strong>$76.7M</strong>. Nothing was re-derived and no new assumption was introduced. But the shape matters more than the total: two of the three components come in <strong>below</strong> Finance's range. The entire gap is disengagement.",
    ),
    (
        "And it is a floor twice over. The attrition log accounts for 60% of the departures the annual report claims for FY2025, so the exits driving the largest component are undercounted before the arithmetic starts.",
        "And the attrition side is a floor. The log accounts for 60% of the departures the annual report claims for FY2025, so the regrettable component is undercounted before the arithmetic starts. Disengagement is not affected by that gap.",
    ),
    (
        "The $42M is not the problem. It is the part Finance can already see.",
        "The $42M is not too small. It is pointed at the wrong component.",
    ),
    ('<div class="kpi-value counter">$143.7M</div>\n      <div class="kpi-note">3.4× the published midpoint</div>',
     '<div class="kpi-value counter">$76.7M</div>\n      <div class="kpi-note">1.8× the published midpoint</div>'),
    ('<div class="kpi-value">+$101.7M</div>\n      <div class="kpi-note">headcount, not unit cost</div>',
     '<div class="kpi-value">+$34.7M</div>\n      <div class="kpi-note">all of it disengagement</div>'),
    ("<h3>Where the $101.7M sits</h3>", "<h3>Where the $34.7M sits</h3>"),
    (
        "Finance's published range against the same unit cost applied to every employee in the file who meets the definition. One component reconciles; two do not.",
        "Finance's published range against the same unit cost applied to the observed population, on an annual basis. Exits and hires are counted inside the 24-month window and halved; the disengaged count is a stock and is not.",
    ),
    # Regrettable row
    ('<div class="bar-name">Regrettable attrition<small>153 exits · $163,200 each</small></div>',
     '<div class="bar-name">Regrettable attrition<small>77 exits a year · $163,200 each</small></div>'),
    ('<div class="bar-line"><div class="bar-fill obs" style="width:38.5%"></div><span class="bar-val"><b>$25.0M</b> · 1.0×</span></div>',
     '<div class="bar-line"><div class="bar-fill obs" style="width:19.2%"></div><span class="bar-val"><b>$12.5M</b> · 0.5×</span></div>'),
    # Disengagement row
    ('<div class="bar-name">Disengagement<small>3,219 staff · $19,200 each</small></div>',
     '<div class="bar-name">Disengagement<small>3,219 staff · $19,200 each · a stock</small></div>'),
    # Hiring row
    ('<div class="bar-name">Hiring inefficiency<small>3,243 agency hires · $17,540 each</small></div>',
     '<div class="bar-name">Hiring inefficiency<small>137 agency hires a year · $17,540 each</small></div>'),
    ('<div class="bar-line"><div class="bar-fill obs" style="width:87.5%"></div><span class="bar-val"><b>$56.9M</b> · 9.5×</span></div>',
     '<div class="bar-line"><div class="bar-fill obs" style="width:3.7%"></div><span class="bar-val"><b>$2.4M</b> · 0.4×</span></div>'),
    (
        "<b>Read it as a scoping error, not a pricing error.</b> Finance's unit costs are accepted in full. What the published figure implies is a disengaged population of 625–781 people against 3,219 in the file, and 228–342 agency hires against 3,243.",
        "<b>Read it as a misallocation, not an underestimate.</b> Finance's unit costs are accepted in full. The published figure implies a disengaged population of 625–781 people; the file holds 3,219. On the other two components Finance's assumptions are more generous than the data supports.",
    ),
    (
        "<b>Defend:</b> $143.7M is Finance's arithmetic, not ours. Every constant is theirs. Concede the range before someone asks for it, the disengagement component moves between $10.9M and $165.3M on the threshold alone.",
        "<b>Defend:</b> $76.7M is Finance's arithmetic, not ours. Every constant is theirs; only the window is ours, and it is stated. Concede the range before someone asks: disengagement moves between $10.9M and $165.3M on the threshold alone, and it is the component carrying the whole gap.",
    ),
    # Recommendations screen
    ('<div class="kpi-value counter">$143.7M</div>\n      <div class="kpi-note">a floor, published figure $42.0M</div>',
     '<div class="kpi-value counter">$76.7M</div>\n      <div class="kpi-note">published figure $42.0M</div>'),
    ("<h4>Re-baseline the business case at $143.7M, and label it a floor</h4>",
     "<h4>Re-baseline the business case at $76.7M, and move the weight to disengagement</h4>"),
    (
        "Applying Finance's own unit costs to the observed population gives <b>$143.7M against the published $42.0M</b>. No constant was changed. The gap is scope: the published figure implies 625–781 disengaged staff against 3,219 in the file, and 228–342 agency hires against 3,243.",
        "Applying Finance's own unit costs to the observed population, on an annual basis, gives <b>$76.7M against the published $42.0M</b>. No constant was changed. The gap is one component: the published figure implies 625–781 disengaged staff against 3,219 in the file. Attrition and agency hiring both come in under Finance's own range.",
    ),
]


def patch_dashboard() -> tuple[int, list[int]]:
    path = ROOT / "dashboard" / "index.html"
    html = path.read_text(encoding="utf-8")
    hits, missed = 0, []
    for i, (old, new) in enumerate(DASH_EDITS):
        if old in html:
            html = html.replace(old, new)
            hits += 1
        elif new not in html:
            missed.append(i)
    path.write_text(html, encoding="utf-8")
    return hits, missed


def main() -> int:
    print("  src/etl.py")
    print(f"    OBS_YEARS added: {patch_etl()}")

    print("  notebooks/03_angle1_cost.ipynb")
    code_hits, md_hits = patch_notebook()
    print(f"    {code_hits} code cells, {md_hits} markdown passages")

    print("  dashboard/index.html")
    hits, missed = patch_dashboard()
    print(f"    {hits} of {len(DASH_EDITS)} edits applied")
    if missed:
        print(f"    NOT MATCHED: index {missed}. Check those by hand.")

    print("\n  Next: .venv\\Scripts\\python.exe tools\\run_notebooks.py 03")
    return 1 if missed else 0


if __name__ == "__main__":
    sys.exit(main())
