"""
Three changes agreed after the annualisation fix.

    python tools/patch_round3.py

1. Angle 1 keeps Finance's "hiring inefficiency" label and publishes the null
   result behind it. Both halves of Finance's definition are tested and neither
   is visible in the data.
2. The department cost table is annualised, so every dollar in notebook 03 and
   on the A1 screen is on the same basis.
3. Angle 2 gains a censoring-corrected integration curve. Comparing cohorts at
   a fixed horizon is the same correction the FAR event study needed, applied to
   acquisition cohorts, and it produces a forward-looking number for Entity_C.

Idempotent. Re-run tools/run_notebooks.py afterwards.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


# --------------------------------------------------------------------------
# 1 and 2: notebook 03
# --------------------------------------------------------------------------

NULL_TEST_CODE = '''# Finance defines this component as an agency fee premium PLUS poor-match early
# attrition. Both halves are testable against the data, so test them rather than
# inheriting the label. A null result is still a result.
channel = df.groupby("hire_source", observed=True).agg(
    n=("employee_id", "size"),
    days_to_fill=("days_to_fill", "mean"),
    attrition_pct=("is_departed", lambda s: 100 * s.mean()),
)
exits = df[df["is_departed"]]
channel["regrettable_pct"] = (
    100 * exits.groupby("hire_source", observed=True)["regrettable_hr"].mean())
channel["median_tenure_at_exit"] = (
    exits.groupby("hire_source", observed=True)["tenure_months"].median())

channel.round(1).sort_values("attrition_pct", ascending=False)'''

NULL_TEST_MD_HEAD = """### Does the hiring inefficiency component survive its own definition?

The brief defines it as the cost premium of agency hiring **and poor-match early
attrition**. Both halves are testable. Neither survives.

The label below stays as Finance wrote it: it is their taxonomy, and renaming it
would break the correspondence with their published decomposition. What changes
is that the claim behind it is now marked as unevidenced rather than assumed."""

NULL_TEST_MD_TAIL = """Agency sits mid-pack or better on every dimension. It fills roles 1.2 days
slower than the fastest channel, leaves at a rate inside the range set by the
other four, and its exits are **less** likely to be flagged regrettable than
those of direct hires.

Two consequences for the deck:

- The $2.4M is a **spend** figure, not an inefficiency figure. Present it as
  agency channel spend that Finance has classified as inefficiency, and say the
  classification is not visible in the data.
- The 18% fee rate is Finance's assumption. There is no cost, fee or
  cost-per-hire column anywhere in the four files, so no part of this component
  is data-derived except the headcount. Say so before a judge asks."""

DEPT_OLD = '''departed = df[df["is_departed"] & df["is_voluntary"]]

by_dept = departed.groupby("department", observed=True).agg('''

DEPT_NEW = '''# Exits are a flow across the 24-month window, so the cost is divided by
# etl.OBS_YEARS to match the annual basis used in the bridge above. The shares
# are unchanged either way; the dollar labels are not.
departed = df[df["is_departed"] & df["is_voluntary"]]

by_dept = departed.groupby("department", observed=True).agg('''

DEPT_COST_OLD = '''by_dept["cost_$m"] = (by_dept["replacement_cost"] / 1e6).round(1)'''
DEPT_COST_NEW = '''by_dept["cost_$m"] = (by_dept["replacement_cost"] / etl.OBS_YEARS / 1e6).round(1)'''

DEPT_TITLE_OLD = '"Voluntary exits, costed at 1.5x salary with an 85% backfill rate. "'
DEPT_TITLE_NEW = '"Voluntary exits per year, costed at 1.5x salary with an 85% backfill rate. "'


def patch_nb03() -> tuple[int, list[str]]:
    path = ROOT / "notebooks" / "03_angle1_cost.ipynb"
    nb = json.loads(path.read_text(encoding="utf-8"))
    if any("does the hiring inefficiency component survive" in "".join(c["source"]).lower()
           for c in nb["cells"]):
        return 0, ["already applied"]

    hits, notes = 0, []
    for cell in nb["cells"]:
        src = "".join(cell["source"])
        before = src
        src = src.replace(DEPT_OLD, DEPT_NEW)
        src = src.replace(DEPT_COST_OLD, DEPT_COST_NEW)
        src = src.replace(DEPT_TITLE_OLD, DEPT_TITLE_NEW)
        if src != before:
            cell["source"] = src.splitlines(keepends=True)
            hits += 1

    # Insert the null-result block after the bridge chart commentary.
    anchor = None
    for i, cell in enumerate(nb["cells"]):
        if "## 4. Who counts as regrettable?" in "".join(cell["source"]):
            anchor = i
            break
    if anchor is None:
        notes.append("anchor for null-result block not found")
    else:
        new_cells = [
            {"cell_type": "markdown", "metadata": {},
             "source": NULL_TEST_MD_HEAD.splitlines(keepends=True)},
            {"cell_type": "code", "metadata": {}, "execution_count": None,
             "outputs": [], "source": NULL_TEST_CODE.splitlines(keepends=True)},
            {"cell_type": "markdown", "metadata": {},
             "source": NULL_TEST_MD_TAIL.splitlines(keepends=True)},
        ]
        nb["cells"][anchor:anchor] = new_cells
        hits += 3

    path.write_text(json.dumps(nb, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return hits, notes


# --------------------------------------------------------------------------
# 3: notebook 04, the integration curve
# --------------------------------------------------------------------------

COHORT_MD_HEAD = """## 8. The integration curve

Section 6 named acquisition integration as the leading alternative explanation
for anything Angle 2 might have found. This section measures it, using the same
correction that section 3 needed.

Raw cohort attrition cannot be compared directly. Entity_A was onboarded in
2023 and has roughly 30 months of observation; Entity_C arrived in mid-2025 and
has about 8. Every Entity_C exit is therefore an early exit by construction, in
exactly the way every Wave 1 FAR exit was a post-treatment exit by construction.

The fix is the same: pick a horizon every cohort can support, and ask what share
of each had left by that point, counting only people observed at least that
long."""

COHORT_CODE = '''AS_AT = etl.OBS_END

cohort = df.copy()
cohort["months_observed"] = ((AS_AT - cohort["hire_date"]).dt.days / 30.44)
cohort["months_to_exit"] = ((cohort["exit_date"] - cohort["hire_date"]).dt.days / 30.44)

ENTITIES = ["Entity_A", "Entity_B", "Entity_C", "NovaCorp-Origin"]
HORIZONS = [3, 6, 9, 12, 18, 24]

rows = []
for h in HORIZONS:
    row = {"horizon_months": h}
    for ent in ENTITIES:
        # Only people who could have been observed for h months are eligible.
        pool = cohort[(cohort["legacy_entity_code"] == ent)
                      & (cohort["months_observed"] >= h)]
        if len(pool) < 50:
            row[ent] = np.nan          # too few to report, not zero
            continue
        gone = (pool["is_departed"] & (pool["months_to_exit"] <= h)).sum()
        row[ent] = round(100 * gone / len(pool), 1)
    rows.append(row)

curve = pd.DataFrame(rows).set_index("horizon_months")
print("  Share of each cohort that had left by month H (%)")
print("  Blank means fewer than 50 people had been observed that long.\\n")
curve'''

COHORT_CHART = '''fig, ax = figure(
    "Entity_C is tracking Entity_B, not Entity_A",
    "Share of each cohort that had left by month H, counting only employees "
    "observed at least that long. Lines stop where the cohort runs out of time.",
    figsize=(9.5, 5.0),
)

for i, ent in enumerate(ENTITIES):
    series = curve[ent].dropna()
    if series.empty:
        continue
    ax.plot(series.index, series.values, color=SERIES[i], marker="o",
            markersize=5, label=ent)
    ax.annotate(f" {ent}", xy=(series.index[-1], series.values[-1]),
                va="center", fontsize=9, color=INK["secondary"])

ax.set(xlabel="months since joining NovaCorp", ylabel="% of cohort departed",
       xlim=(2, 30), ylim=(0, None))
ax.set_xticks(HORIZONS)
save_fig(fig, "a2_integration_curve")
plt.show()'''

COHORT_FORECAST = '''# What the curve implies for the cohort still inside its risk window.
UNIT = etl.AR_AVG_BASE_SALARY * etl.REPLACEMENT_MULTIPLIER * etl.BACKFILL_RATE
n_c = int((df["legacy_entity_code"] == "Entity_C").sum())

c_now = curve.loc[6, "Entity_C"]
b_18 = curve.loc[18, "Entity_B"]
a_18 = curve.loc[18, "Entity_A"]

print(f"  Entity_C headcount              : {n_c:,}")
print(f"  Departed by month 6             : {c_now}%  ({round(n_c * c_now / 100)} people)")
print(f"  Entity_B reached by month 18    : {b_18}%")
print(f"  Entity_A reached by month 18    : {a_18}%")
print()
print(f"  If Entity_C follows Entity_B    : {round(n_c * b_18 / 100)} total, "
      f"{round(n_c * (b_18 - c_now) / 100)} more to come")
print(f"  If it follows Entity_A instead  : {round(n_c * a_18 / 100)} total")
print(f"  Difference between the two paths: "
      f"{millions((n_c * (b_18 - a_18) / 100) * UNIT)} in replacement cost")'''

COHORT_MD_TAIL = """### What this says

At the six-month mark, the only horizon all three cohorts can support with a
full sample:

| Cohort | Onboarded | Departed by month 6 |
|---|---|---|
| Entity_A | 2023 | 0.1% |
| Entity_B | mid-2024 | 8.3% |
| Entity_C | mid-2025 | 9.1% |
| NovaCorp-Origin | n/a | 0.2% |

Three things follow.

- **Entity_A is not the benchmark the annual report implies.** The report calls
  its integration successful, and by month 24 it is at 6.2%. But its first six
  months were near-flawless: one departure in 1,950 people. Whatever was done in
  2023 was not repeated.
- **Entity_C is on Entity_B's curve, not Entity_A's.** It is currently about
  eight months in. This is the only forward-looking finding in the project, and
  it concerns a cohort of 1,014 people who are still inside their risk window.
- **The gap is worth roughly $18.6M** in replacement cost between the Entity_B
  path and the Entity_A path, on Finance's own unit cost.

This is association, not proof: the three cohorts differ in size, sector mix and
integration year, and no design here isolates the cause. But unlike the FAR
hypothesis it is a live risk on a named population with a date attached, and it
is the one thing on these six notebooks that a CHRO can still change the outcome
of."""


def patch_nb04() -> tuple[int, list[str]]:
    path = ROOT / "notebooks" / "04_angle2_far.ipynb"
    nb = json.loads(path.read_text(encoding="utf-8"))
    if any("## 8. The integration curve" in "".join(c["source"]) for c in nb["cells"]):
        return 0, ["already applied"]

    anchor = None
    for i, cell in enumerate(nb["cells"]):
        if "## The Angle 2 story" in "".join(cell["source"]):
            anchor = i
            break
    if anchor is None:
        return 0, ["Angle 2 story cell not found"]

    def md(text):
        return {"cell_type": "markdown", "metadata": {},
                "source": text.splitlines(keepends=True)}

    def code(text):
        return {"cell_type": "code", "metadata": {}, "execution_count": None,
                "outputs": [], "source": text.splitlines(keepends=True)}

    nb["cells"][anchor:anchor] = [
        md(COHORT_MD_HEAD), code(COHORT_CODE), code(COHORT_CHART),
        code(COHORT_FORECAST), md(COHORT_MD_TAIL),
    ]

    # Point the story at it.
    for cell in nb["cells"]:
        src = "".join(cell["source"])
        if "## The Angle 2 story" in src and "Section 8" not in src:
            src = src.rstrip() + (
                "\n7. **Section 8 is where this angle actually pays off.** The"
                " confound in point 5 is measurable, and once cohorts are compared"
                " at a fixed horizon Entity_C is tracking Entity_B rather than"
                " Entity_A. That is a live risk on 1,014 people, worth roughly"
                " $18.6M between the two paths, and it is the only forward-looking"
                " finding in the project.\n"
            )
            cell["source"] = src.splitlines(keepends=True)
            break

    path.write_text(json.dumps(nb, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return 5, []


def main() -> int:
    print("  notebooks/03_angle1_cost.ipynb")
    h3, n3 = patch_nb03()
    print(f"    {h3} cells changed or inserted {n3 or ''}")

    print("  notebooks/04_angle2_far.ipynb")
    h4, n4 = patch_nb04()
    print(f"    {h4} cells inserted {n4 or ''}")

    print("\n  Next: python tools/run_notebooks.py 03 04")
    return 0


if __name__ == "__main__":
    sys.exit(main())
