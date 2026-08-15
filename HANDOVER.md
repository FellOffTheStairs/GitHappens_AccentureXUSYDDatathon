# NovaCorp People Analytics: team handover

Behind the CHRO deck and dashboard, with every figure traced to the code that
produced it.

**Status.** Analysis complete and reproducible. Open items in section 10.

---

## 1. The decision question

The brief asks what drives NovaCorp's people cost, which parts are tractable,
and where to prioritise. We treated the $42M as a hypothesis, not a
conclusion, and tested three mechanisms against the four datasets and the
FY2025 annual report. Two did not survive, and that shaped the recommendation
more than anything we confirmed.

**In one line:** NovaCorp does not have an attrition problem. It has a
measurement problem, and the cost sits with people who never resign.

---

## 2. How the work is organised

```
src/etl.py            all data transformation, one place
clean/*.parquet       seven cached tables
notebooks/00 to 05    the analysis
dashboard/index.html  four interactive screens
```

`python tools/run_notebooks.py` regenerates everything from `src/etl.py`, so a
constant changed there propagates everywhere. `FUNCTIONS.md` explains each
file.

---

## 3. Foundation: the published attrition rate

The report states 10.4% voluntary attrition. It reproduces exactly:

```
full historical roster        13,403
still active                  12,003
difference, all departures     1,400   over 24 months
1,400 / 13,403               = 10.4%
```

All seven departments reconcile to the decimal on the same formula. Three
things are wrong with the label, all pushing the same direction: 267 of the
1,400 are involuntary, the window is 24 months not 12, and the denominator is
the roster rather than active headcount.

**Corrected: 4.7% annual voluntary attrition** (range 4.6% to 5.7% depending
on which twelve months). Against AHRI's 15.2% national average and ABS's 7.9%
sector mobility, NovaCorp retains well. **The FY2026 sub-9.5% target is
already met, twice over,** so a programme measured against it could succeed or
fail without the number moving. Reproducible in `02_data_quality.ipynb §6`.
Department ranking is unaffected, since every department uses the same
formula.

---

## 4. The $42M is misallocated, not too small

Finance's own unit costs, applied to the actual population on an annual
basis (their ranges are per year; the data covers two, so flows are halved
and stocks are not):

| Component | Type | Finance | Per year | Cost | vs range |
|---|---|---|---|---|---|
| Regrettable attrition | flow | $22-25M | 76 exits | $12.5M | 0.5x |
| Disengagement | stock | $12-15M | 3,219 people | $61.8M | 4.1x |
| Hiring inefficiency | flow | $4-6M | 137 hires | $2.4M | 0.4x |
| **Total** | | **$42.0M** | | **$76.7M** | **1.8x** |

Two components land *below* Finance's range. The entire gap is disengagement:
a misallocation, not an underestimate. Reproducible in
`03_angle1_cost.ipynb §1-3`.

**The measurement gap inside it.** HR's flag catches 153 regrettable exits;
an evidence test (voluntary, high-potential or top-two performance rating)
finds 496. Four in five, 395 people, are invisible to the business case:
**$64.5M over the two years analysed, about $32M a year.** Of those 395, 224
left for career advancement and 98 for a better opportunity against 18
citing compensation, a progression problem, not a pay problem.

---

## 5. Manager effectiveness predicts disengagement, not attrition

| Manager rating | n | Persistently disengaged |
|---|---|---|
| 4.0+ | 2,874 | 4.5% |
| 3.5-4.0 | 2,235 | 14.7% |
| 3.0-3.5 | 2,256 | 27.0% |
| 2.5-3.0 | 1,912 | 45.0% |
| Below 2.5 | 1,880 | 68.8% |

15.5x across the scale, monotonic at every step, n = 11,157. But manager
rating against actual departures gives r = -0.012, indistinguishable from
zero, and disengagement against attrition is r = -0.002. **The case for
acting is productivity, not retention.** Two limits worth carrying into the
deck: both measures come from the same survey response, and team size,
workload and resourcing are not held constant, so a poorly rated manager may
be running an under-resourced team. Reproducible in
`05_angle3_silence.ipynb §6`.

---

## 6. The early-warning signal

| Signal | n | Attrition | Lift | Available |
|---|---|---|---|---|
| Low engagement score | 2,964 | 6.3% | 1.07x | after scoring |
| Declining score | 589 | 8.0% | 1.36x | needs two waves |
| **Went silent** | **441** | **12.7%** | **2.16x** | **day the wave closes** |

Baseline 5.9% among the 11,518 employees issued three or more waves. **The
signal HR watches has almost no predictive power; the one it discards has
twice as much and arrives sooner.** Leavers answer roughly 15 points below
stayers from at least 18 months out with no late collapse, so the mechanism
is disengagement, not notice-period checkout.

Run naively, non-response looks like a 2.9x signal, but that is survey
exposure: Entity_C joined at wave 5, so one missed email makes 1,014 people
look like non-responders. Conditioning on three or more waves removes the
artefact and leaves the 2.16x that holds. **This cannot see new starters**,
who are excluded by the three-wave requirement and are the highest-risk
group.

Reproducible in `05_angle3_silence.ipynb §1-5`.

---

## 7. Entity_C: the one forward-looking risk

Cohorts can't be compared raw (Entity_A has ~30 months of observation,
Entity_C ~8), so every comparison is measured at a fixed horizon:

| Cohort | Onboarded | Departed by month 6 |
|---|---|---|
| Entity_A | 2023 | 0.1% (1 of 1,950) |
| Entity_B | mid-2024 | 8.3% (156 of 1,884) |
| Entity_C | mid-2025 | 9.1% (92 of 1,014) |
| NovaCorp-Origin | n/a | 0.2% |

**Entity_C is on Entity_B's curve, not Entity_A's.** Projected to month 18:
157 departures on the Entity_B path against 43 on Entity_A's, **an $18.6M
gap by month 18.** Association, not proof, and Entity_C has only two points
on the curve, but this is the only forward-looking finding in the project
and the window is still open. Reproducible in `04_angle2_far.ipynb §8`.

---

## 8. What we tested and rejected

**The Financial Accountability Regime.** A naive before/after on the March
2024 banking commencement shows a 9x jump in regulated exits, an artefact of
the data starting six weeks before the rule took effect. Corrected against
an already-treated control over identical months: **+1.4 exits per 1,000,
95% interval -26.4 to +29.2.** Not identified is not the same as no effect:
476 regulated employees producing 39 exits cannot resolve one in either
direction. Recommended spend: nil.

**Agency hiring.** 1.2-day spread in time to fill across five channels,
attrition inside the range every other channel sets, and agency exits *less*
likely to be flagged regrettable than direct hires. No cost or fee column
exists anywhere in the four files, so the number some models attach here is
an assumed rate on an uncorrected headcount, not a measurement.

---

## 9. Recommendations

| # | Action | Exposure | Cost to try | When you know | Evidence |
|---|---|---|---|---|---|
| 01 | Non-response alert | $1.8M | Under $50K | Next survey wave | Identified |
| 02 | Redefine regrettable exit | $64.5M (2yr) | Nil | Next exit cycle | Directly observed |
| 03 | Entity_C review | $18.6M (mo 18) | Team time | Four months | Associational |
| 04 | Restate baseline at $76.7M | Correct scope | CFO time | FY2027 planning | Threshold-sensitive |
| 05 | Fix three data defects | Unblocks 01, 04 | Data owner time | Ongoing | Verified |
| X | FAR retention programme | Do not fund | $0 | n/a | Not identified |

Ordered by speed to a measurable result, not dollar size. Exposure addressed
is not cash saved; none of these has been tested at NovaCorp.

**The closing frame.** The FY2025 report says budgets are set aside for
"People Reinvention" three times, never with a figure, while every other
initiative carries one. The deck's final slide fills that blank as a
priority order: Disengagement $61.8M/yr, Entity_C $18.6M by month 18,
Regrettable exits $12.5M/yr, Agency $2.4M/yr.

---

## 10. Open items

| Item | Impact |
|---|---|
| Attrition log reconciles to 60% of reported FY2025 departures | Attrition costs stay a floor |
| New starters excluded from the early-warning estimate | Highest-risk group unmeasured |
| Manager finding not controlled for team context | Constrains the recommendation to a diagnostic |

---

## 11. Ethics

- No individual is labelled a flight risk; cohorts are a screen for a human
  conversation.
- No automated employment decision is recommended anywhere.
- Demographic fields are not used to rank, predict or prioritise
  individuals.
- Causal language is used only where a design supports it, which in this
  project is nowhere: every relationship is stated as association.
- Every threshold we chose is sensitivity-tested and published.
- Exit reasons are treated as directional, per the brief's own note that 40
  to 60% don't reflect the primary driver.
- Rejected hypotheses are reported, not dropped: two of three mechanisms
  didn't survive, and both are in the deck.

---

## 12. Reproducing everything

```powershell
cd D:\Novacorp\GitHappens_AccentureXUSYDDatathon
python src\run_pipeline.py Accenture_Case_Comp_Data.zip
python tools\run_notebooks.py
start dashboard\index.html
```

Every deck figure traces to a notebook section, mapped in the deck's
appendix A1 and in `FUNCTIONS.md`.
