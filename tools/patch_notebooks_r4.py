"""
Make the last three dashboard figures reproducible from the notebooks.

    python tools/patch_notebooks_r4.py

Adds two sections:

  02  reverse-engineers the annual report's 10.4% and states the corrected
      annual voluntary rate
  05  manager effectiveness against persistent disengagement, with the causal
      claim narrowed against attrition

Uses numpy only. scipy is not in the project venv and this is not the week to
add a dependency. Confidence intervals use the Fisher z transform; the t
statistic is computed directly.

Idempotent. Re-run tools/run_notebooks.py 02 05 afterwards.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


# --------------------------------------------------------------------------
# 02: the reconciliation
# --------------------------------------------------------------------------

RECON_MD = """## 6. What the annual report's 10.4% actually counts

Section 2 established that the headline rate does not reconcile. This section
works out what it does reconcile to, which turns out to be exact.

The test: if the report's "voluntary attrition" were computed as every
departure in the file divided by the full historical roster, the departmental
breakdown on page 8 would fall out of this dataset without adjustment. Seven
departments is enough to rule out coincidence."""

RECON_CODE = '''# The published departmental rates, transcribed from the FY2025 report, page 8.
PUBLISHED = {
    "Retail Banking": 9.3, "Technology": 10.4, "Risk & Compliance": 11.8,
    "Insurance": 10.3, "Wealth Management": 10.5, "Corporate Operations": 11.6,
    "Executive Leadership": 8.3,
}

roster = emp.groupby("department", observed=True).size()
active = (emp[emp["status"].str.lower() == "active"]
          .groupby("department", observed=True).size())

check = pd.DataFrame({"roster": roster, "active": active})
check["departed"] = check["roster"] - check["active"]
check["computed_pct"] = (100 * check["departed"] / check["roster"]).round(1)
check["published_pct"] = pd.Series(PUBLISHED)
check["match"] = (check["computed_pct"] - check["published_pct"]).abs() < 0.1

print(f"  Departments reconciling exactly: {check['match'].sum()} of {len(check)}")
check'''

RECON_CODE2 = '''# The same formula at company level, and the three things wrong with the label.
total_roster, total_active = len(emp), int((emp["status"].str.lower() == "active").sum())
all_exits = len(att)
voluntary = int(att["exit_type"].str.lower().eq("voluntary").sum())
involuntary = all_exits - voluntary

print("  The published formula")
print(f"    full historical roster            {total_roster:>7,}")
print(f"    still active                      {total_active:>7,}")
print(f"    difference, all departures        {all_exits:>7,}   over 24 months")
print(f"    {all_exits:,} / {total_roster:,}                    "
      f"{100 * all_exits / total_roster:>6.1f}%   published: 10.4%")

print("\\n  What the label gets wrong")
print(f"    1. not voluntary   {involuntary:,} of {all_exits:,} exits are involuntary "
      f"({100 * involuntary / all_exits:.0f}%)")
print(f"    2. not annual      the window is 24 months, not 12")
print(f"    3. not headcount   denominator is the roster, not the {total_active:,} active")

print("\\n  Corrected, on the same data")
per_year = voluntary / etl.OBS_YEARS
print(f"    voluntary exits, 24 months        {voluntary:>7,}")
print(f"    per year                          {per_year:>7,.0f}")
print(f"    against {total_active:,} active            {100 * per_year / total_active:>6.1f}%")

# The rate depends on which twelve months are chosen, so give the range.
att_dates = att.assign(vol=att["exit_type"].str.lower().eq("voluntary"))
windows = {
    "FY2025 (Jul 24 to Jun 25)": ("2024-07-01", "2025-06-30"),
    "calendar 2024": ("2024-01-01", "2024-12-31"),
    "calendar 2025": ("2025-01-01", "2025-12-31"),
}
print("\\n  Sensitivity to the twelve months chosen")
for label, (lo, hi) in windows.items():
    n = int((att_dates["vol"] & att_dates["exit_date"].between(lo, hi)).sum())
    print(f"    {label:<28} {n:>4} exits   {100 * n / total_active:>5.1f}%")'''

RECON_MD2 = """### What this changes

The formula reconciles on all seven departments and at company level, so there
is no ambiguity about what was computed. Three things are wrong with the label,
and all three push the published figure in the same direction:

- **Not voluntary.** 267 of the 1,400 departures are involuntary exits.
- **Not annual.** The window is 24 months.
- **Not headcount.** The denominator includes everyone who left.

Corrected, annual voluntary attrition is **4.7%**, running between 4.6% and 5.7%
depending on which twelve months are chosen.

Two consequences worth carrying forward:

1. **The FY2026 target is measuring the wrong quantity.** Guidance sets
   voluntary attrition below 9.5% against a stated 10.4%. On a like-for-like
   basis the company has been at roughly half that for both years in the data,
   so a programme could succeed or fail without the metric moving.
2. **NovaCorp does not have a volume problem.** Against AHRI's 15.2% Australian
   organisational average for December 2025 and ABS Financial and Insurance
   Services job mobility of 7.9%, it is losing people slowly. Which component of
   the $42M is worth attention becomes a question about *who* leaves, not how
   many, and that is what Angle 1 goes on to test.

The departmental *ranking* is unaffected: every department is computed the same
way, so Risk and Compliance sitting above the firm average remains true."""


# --------------------------------------------------------------------------
# 05: manager effectiveness
# --------------------------------------------------------------------------

MGR_MD = """## 6. What sits underneath the silence

Sections 1 to 5 establish that non-response predicts exit. They do not say what
the disengagement is *about*. The survey carries eight dimensions, and one of
them separates the population far more sharply than the rest.

This section is deliberately structured as two claims: a large association, and
then an explicit statement of what that association does not license."""

MGR_CODE = '''# One row per employee: mean manager rating, and whether they meet the
# persistent-disengagement definition used throughout (composite below 3.0 in
# two or more answered waves). Restricted to employees with 2+ answered waves,
# since the definition cannot apply below that.
answered = eng[eng["responded"]].copy()

per_emp = answered.groupby("employee_id", observed=True).agg(
    mgr_rating=("manager_effectiveness", "mean"),
    waves_answered=("composite", "size"),
    waves_low=("composite", lambda s: (s < 3.0).sum()),
)
per_emp = per_emp[per_emp["waves_answered"] >= 2]
per_emp["disengaged"] = per_emp["waves_low"] >= 2

BANDS = [0, 2.5, 3.0, 3.5, 4.0, 5.01]
LABELS = ["<2.5", "2.5-3.0", "3.0-3.5", "3.5-4.0", "4.0+"]
per_emp["band"] = pd.cut(per_emp["mgr_rating"], BANDS, labels=LABELS, right=False)

gradient = per_emp.groupby("band", observed=True).agg(
    n=("disengaged", "size"), disengaged=("disengaged", "sum"))
gradient["pct"] = (100 * gradient["disengaged"] / gradient["n"]).round(1)

print(f"  Employees with 2+ answered waves: {len(per_emp):,}")
gradient'''

MGR_CHART = '''fig, ax = figure(
    "Disengagement falls at every step of the manager-rating scale",
    "Persistent disengagement means a composite score below 3.0 in two or more "
    "answered waves. Bars are labelled with the band size.",
    figsize=(9.5, 4.6),
)

x = np.arange(len(gradient))
bars = ax.bar(x, gradient["pct"], width=0.62, color=SERIES[1])
# The healthiest band in slot 1, so the contrast reads without a legend.
bars[-1].set_color(SERIES[0])

for xi, (_, row) in zip(x, gradient.iterrows()):
    ax.annotate(f"{row['pct']:.1f}%", xy=(xi, row["pct"]), xytext=(0, 5),
                textcoords="offset points", ha="center", fontsize=10,
                color=INK["primary"], fontweight="600")
    inside = row["pct"] > 10          # a short bar cannot hold a label
    ax.annotate(f"n = {int(row['n']):,}", xy=(xi, 1.5 if inside else row["pct"] + 4.5),
                ha="center", fontsize=9,
                color="white" if inside else INK["secondary"])

ax.set_xticks(x, gradient.index)
ax.set(xlabel="employee's mean rating of their manager",
       ylabel="% persistently disengaged", ylim=(0, 80))
save_fig(fig, "a3_manager_gradient")
plt.show()'''

MGR_STATS = '''def pearson(x, y):
    """r, t statistic and 95% interval, without scipy.

    The interval uses the Fisher z transform, which is the standard approach
    and needs nothing beyond numpy."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    n = len(x)
    r = float(np.corrcoef(x, y)[0, 1])
    t = r * np.sqrt((n - 2) / (1 - r ** 2))
    z = np.arctanh(r)
    se = 1 / np.sqrt(n - 3)
    lo, hi = np.tanh(z - 1.96 * se), np.tanh(z + 1.96 * se)
    return r, t, lo, hi, n


# The association, as an effect size on the two ends of the scale.
low = per_emp[per_emp["mgr_rating"] < 2.5]
high = per_emp[per_emp["mgr_rating"] >= 4.0]
ratio = low["disengaged"].mean() / high["disengaged"].mean()

print("  ASSOCIATION with disengagement")
print(f"    manager rated <2.5   {100 * low['disengaged'].mean():>5.1f}%  (n = {len(low):,})")
print(f"    manager rated >=4.0  {100 * high['disengaged'].mean():>5.1f}%  (n = {len(high):,})")
print(f"    ratio                {ratio:>5.1f}x")

r, t, lo, hi, n = pearson(per_emp["mgr_rating"], per_emp["disengaged"].astype(int))
print(f"    r = {r:.3f}  t = {t:.1f}  95% CI [{lo:.3f}, {hi:.3f}]  n = {n:,}")

# The same variable against attrition, which is the claim NOT being made.
linked = (df[["employee_id", "is_departed"]]
          .merge(per_emp.reset_index(), on="employee_id", how="inner"))

print("\\n  ASSOCIATION with attrition")
for label, col in [("manager rating", "mgr_rating"),
                   ("disengagement", "disengaged")]:
    r2, t2, lo2, hi2, n2 = pearson(linked[col].astype(float),
                                   linked["is_departed"].astype(int))
    verdict = "zero is inside the interval" if lo2 <= 0 <= hi2 else "interval excludes zero"
    print(f"    {label:<16} r = {r2:+.3f}  t = {t2:+.1f}  "
          f"95% CI [{lo2:+.3f}, {hi2:+.3f}]  {verdict}")'''

MGR_MD2 = """### What the evidence supports

Employees who rate their manager poorly are far more likely to be persistently
disengaged. The gradient is monotonic across all five bands, so this is not a
threshold artefact, and it holds on 11,157 employees.

It is also the most controllable finding in these six notebooks. Manager
capability is something NovaCorp already develops, and the next survey wave
measures it directly, which makes it testable rather than merely arguable.

### What it does not support

It does not show that poor managers cause people to leave. Manager rating
against attrition gives a correlation of roughly -0.01 with zero comfortably
inside the interval, and persistent disengagement against attrition is smaller
still.

That is a real constraint on the recommendation, not a hedge. The case for
acting on manager capability is a **productivity and working-conditions case**.
Selling it as an attrition-reduction programme would claim something these data
do not show, and it would be measured against a metric that Angle 3 has already
shown moves for other reasons.

Two limits worth stating alongside it:

- **Same-source bias.** Both variables come from the same survey response, so an
  employee who is disengaged may rate everything lower, including their manager.
  Nothing here separates the two.
- **Team context is not controlled.** Span of control, resourcing and workload
  all sit in `analysis_df` and none of them are held constant. A manager with a
  poor rating may be managing an under-resourced team rather than managing
  badly, which is why the recommendation is a diagnostic rather than a
  performance action."""


def insert_before(nb, anchor_text, cells):
    for i, cell in enumerate(nb["cells"]):
        if anchor_text in "".join(cell["source"]):
            nb["cells"][i:i] = cells
            return True
    return False


def md(t):
    return {"cell_type": "markdown", "metadata": {}, "source": t.splitlines(keepends=True)}


def code(t):
    return {"cell_type": "code", "metadata": {}, "execution_count": None,
            "outputs": [], "source": t.splitlines(keepends=True)}


def main() -> int:
    ok = True

    p2 = ROOT / "notebooks" / "02_data_quality.ipynb"
    nb2 = json.loads(p2.read_text(encoding="utf-8"))
    if any("What the annual report's 10.4% actually counts" in "".join(c["source"])
           for c in nb2["cells"]):
        print("  02: already applied")
    else:
        done = insert_before(nb2, "## Carry these forward", [
            md(RECON_MD), code(RECON_CODE), code(RECON_CODE2), md(RECON_MD2)])
        if done:
            p2.write_text(json.dumps(nb2, indent=1, ensure_ascii=False) + "\n",
                          encoding="utf-8")
            print("  02: 4 cells inserted")
        else:
            print("  02: anchor not found")
            ok = False

    p5 = ROOT / "notebooks" / "05_angle3_silence.ipynb"
    nb5 = json.loads(p5.read_text(encoding="utf-8"))
    if any("What sits underneath the silence" in "".join(c["source"])
           for c in nb5["cells"]):
        print("  05: already applied")
    else:
        done = insert_before(nb5, "## The Angle 3 story", [
            md(MGR_MD), code(MGR_CODE), code(MGR_CHART), code(MGR_STATS), md(MGR_MD2)])
        if done:
            p5.write_text(json.dumps(nb5, indent=1, ensure_ascii=False) + "\n",
                          encoding="utf-8")
            print("  05: 5 cells inserted")
        else:
            print("  05: anchor not found")
            ok = False

    print("\n  Next: python tools/run_notebooks.py 02 05")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
