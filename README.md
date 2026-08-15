# NovaCorp People Analytics: team handover

**What this covers.** The analysis behind the 15-slide CHRO deck and the
interactive dashboard, with every figure traced to the code that produced it.

**Audience.** The team, and anyone picking this up after us.

**Status.** Analysis complete and reproducible. Four items remain open and are
listed in section 10.

---

## 1. The decision question

The brief asks what is driving NovaCorp's people cost, which components are
most tractable, and where the CHRO and CFO should prioritise.

We treated the $42M as a starting hypothesis rather than a conclusion, and
tested three mechanisms against the four datasets and the FY2025 annual report.
Two of the three did not survive. That shaped the recommendation more than
anything we confirmed.

**The answer in one line.** NovaCorp does not have an attrition problem. It has
a measurement problem, and the cost sits with people who never resign.

---

## 2. How the work is organised

```
src/etl.py            all data transformation, one place
clean/*.parquet       seven cached tables
notebooks/00 to 05    the analysis
dashboard/index.html  four interactive screens
figures/              15 charts
```

Run `python tools/run_notebooks.py` to regenerate everything. `src/etl.py` holds
every constant, so changing an assumption there propagates to all six notebooks
and all figures at once.

`FUNCTIONS.md` explains each file in plain terms.

---

## 3. The foundation finding: the published attrition rate

**This is the first thing to present and the first thing a CFO will recompute.**

The FY2025 report states 10.4% voluntary attrition. We reproduced it exactly:

```
full historical roster        13,403
still active                  12,003
difference, all departures     1,400   over 24 months
1,400 / 13,403               = 10.4%
```

All seven departments reconcile to the decimal on the same formula: Retail
Banking 9.3%, Technology 10.4%, Risk and Compliance 11.8%, Insurance 10.3%,
Wealth Management 10.5%, Corporate Operations 11.6%, Executive Leadership 8.3%.

Three things are wrong with the label, all pushing the same direction:

1. **Not voluntary.** 267 of the 1,400 are involuntary exits.
2. **Not annual.** The window is 24 months.
3. **Not headcount.** The denominator counts everyone who ever left.

**Corrected: 4.7% annual voluntary attrition** (1,133 voluntary exits over two
years against 12,003 active). The range is 4.6% to 5.7% depending on which
twelve months are chosen.

Against AHRI's 15.2% Australian organisational average and ABS Financial and
Insurance Services job mobility of 7.9%, NovaCorp is retaining well.

**Consequence for the deck.** The FY2026 target of sub-9.5% is already met
twice over. Any programme measured against it could succeed or fail without the
number moving. Reproducible in `02_data_quality.ipynb`, section 6.

**Note for the team:** departmental *ranking* is unaffected, since every
department is computed identically. Risk and Compliance sitting above the firm
average remains true.

---

## 4. Cost mechanism 1: the $42M is misallocated

We applied Finance's own unit costs, unchanged, to the population actually in
the data, on an annual basis. Nothing was re-derived.

| Component | Type | Finance | Observed per year | Cost | vs range |
|---|---|---|---|---|---|
| Regrettable attrition | flow | $22 to 25M | 76 exits | $12.5M | 0.5x |
| Disengagement | stock | $12 to 15M | 3,219 people | $61.8M | 4.1x |
| Hiring inefficiency | flow | $4 to 6M | 137 hires | $2.4M | 0.4x |
| **Total** | | **$42.0M** | | **$76.7M** | **1.8x** |

**The critical methodological point.** Finance's ranges are annual; the data
covers 24 months. Counts of *events* (exits, hires) must be halved. Counts of
people in a *state* (currently disengaged) must not. Mixing the two produces
$143.7M, which is wrong. `OBS_YEARS` in `src/etl.py` encodes this.

**The claim is not "understated threefold".** Two of three components come in
*below* Finance's own range. The entire gap is disengagement, which makes the
story a misallocation rather than an underestimate. That is a stronger and more
defensible position.

Reproducible in `03_angle1_cost.ipynb`, sections 1 to 3.

### The measurement gap inside it

HR's `regrettable_flag` identifies 153 exits. An evidence test (voluntary
departure by someone flagged high-potential or rated in the top two performance
bands) identifies 496. They agree on 101.

**Four in five regrettable departures are invisible to the business case,
worth $64.5M.**

Of the 395 missed, **224 left for career advancement and 98 for a better
opportunity, against 18 citing compensation.** This is a progression problem,
not a pay problem, and it points the intervention somewhere specific.

---

## 5. Cost mechanism 2: manager effectiveness

The strongest relationship in the survey.

| Manager rating | n | Persistently disengaged |
|---|---|---|
| 4.0 and above | 2,874 | 4.5% |
| 3.5 to 4.0 | 2,235 | 14.7% |
| 3.0 to 3.5 | 2,256 | 27.0% |
| 2.5 to 3.0 | 1,912 | 45.0% |
| Below 2.5 | 1,880 | 68.8% |

15.5x across the scale, monotonic at every step, n = 11,157.

**And immediately, the narrowing.** Manager rating against *attrition* gives
r = -0.012 with zero comfortably inside the interval. Disengagement against
attrition is r = -0.002.

**So the case for acting is a productivity and working-conditions case, not a
retention case.** Selling it as an attrition programme would claim something
these data do not show.

Two limits to state on the slide, not bury:

- **Same-source bias.** Both measures come from one survey response. A
  disengaged employee may rate everything lower, including their manager.
- **Team context is uncontrolled.** Span, workload and resourcing all sit in
  `analysis_df` and none are held constant. A poorly rated manager may be
  running an under-resourced team. This is why we recommend a diagnostic rather
  than a performance action.

Reproducible in `05_angle3_silence.ipynb`, section 6.

---

## 6. The early-warning signal

Employees who answered the survey before and then miss two consecutive waves
leave at more than twice the rate of their peers.

| Signal | n | Attrition | Lift | Available |
|---|---|---|---|---|
| Low engagement score | 2,964 | 6.3% | 1.07x | after scores are processed |
| Declining score | 589 | 8.0% | 1.36x | needs two waves of history |
| **Went silent** | **441** | **12.7%** | **2.16x** | **the day the wave closes** |

Baseline is 5.9% among the 11,518 employees issued three or more waves.

**The signal HR watches has almost no predictive power. The signal it discards
has twice as much and arrives sooner.**

Leavers answer roughly 15 points below stayers from at least 18 months out,
with no late collapse, so the mechanism is disengagement rather than
notice-period checkout. The intervention window is quarters.

### The correction that makes it real

Run naively, "never responded" appears to carry a 2.9x lift. That is survey
exposure, not disengagement: Entity_C joined the platform at wave 5, so one
missed email makes 1,014 people look like career non-responders. Entity_C's
31.4% non-response sits with the second-lowest attrition in the company.

Conditioning on three or more waves issued removes the artefact and leaves the
2.16x that holds. **Showing the wrong answer first is the analytical
contribution here.**

**What it cannot see:** requiring three waves removes almost everyone hired in
the last year, and that is the group with both the highest non-response and the
highest attrition. The estimate is clean within a long-tenured population and
silent about new starters.

Reproducible in `05_angle3_silence.ipynb`, sections 1 to 5.

---

## 7. The forward-looking risk: Entity_C

Acquisition cohorts cannot be compared raw. Entity_A has roughly 30 months of
observation and Entity_C about 8, so every Entity_C exit is early by
construction.

Measured at a fixed horizon, counting only people observed that long:

| Cohort | Onboarded | Departed by month 6 |
|---|---|---|
| Entity_A | 2023 | 0.1% (1 of 1,950) |
| Entity_B | mid-2024 | 8.3% (156 of 1,884) |
| Entity_C | mid-2025 | 9.1% (92 of 1,014) |
| NovaCorp-Origin | n/a | 0.2% |

**Entity_C is on Entity_B's curve, not Entity_A's.** Projected to month 18: 157
departures on the Entity_B path against 43 on the Entity_A path. **$18.6M
between them.**

Also notable: Entity_A's first six months were near flawless, one departure in
1,950 people. The annual report calls that integration successful without
quantifying it. Whatever was done in 2023 was not repeated.

**This is the only forward-looking finding in the project.** Everything else
describes what has already happened. Association rather than proof, and
Entity_C has two points on the curve, but the window is still open.

Reproducible in `04_angle2_far.ipynb`, section 8.

---

## 8. What we tested and rejected

Both would have cost money to chase.

### The Financial Accountability Regime

FAR commenced for banking in March 2024 and insurance in March 2025. The
twelve-month stagger looks like a natural experiment and it is the right
instinct.

It does not survive the observation window. The data begins six weeks before
the first wave, so a before-and-after comparison has 1.4 months of "before"
against 21.6 months of "after". That alone manufactures a 9x jump.

Run properly, using Wave 2 against an already-treated Wave 1 over identical
calendar months: **+1.4 exits per 1,000, standard error 14.2, interval -26.4 to
+29.2.**

**"Not identified" is not "no effect."** 476 regulated employees producing 39
exits cannot resolve an effect of any plausible size in either direction. Say
this precisely; it will be challenged.

Recommended spend: nil. Revisit with a second post-commencement year.

### Agency hiring

Finance defines hiring inefficiency as agency fee premium plus poor-match early
attrition. Both halves are testable and neither is visible:

| Channel | Days to fill | Attrition | Regrettable share of exits |
|---|---|---|---|
| Agency | 52.5 | 9.8% | 10.4% |
| Direct | 51.4 | 9.9% | 12.0% |
| Referral | 52.1 | 9.7% | 12.2% |
| Acquisition | 51.8 | 10.9% | 10.5% |
| Graduate | 51.3 | 13.8% | 10.6% |

A 1.2-day spread across five channels. Agency is mid-pack or better on every
dimension and its exits are *less* likely to be flagged regrettable than direct
hires.

There is also **no cost, fee or cost-per-hire column in any of the four files**,
so the 18% fee is Finance's assumption. Nothing in this component is
data-derived except the headcount.

We kept Finance's label because it is their taxonomy, and marked the claim
behind it unevidenced.

---

## 9. Recommendations as they appear in the deck

| # | Action | Exposure | Cost to try | When you know | Evidence |
|---|---|---|---|---|---|
| 01 | Non-response alert | $1.8M | Under $50K | Next survey wave | Identified |
| 02 | Redefine regrettable exit | $64.5M | Nil | Next exit cycle | Directly observed |
| 03 | Entity_C integration review | $18.6M | Team time | Four months | Associational |
| 04 | Restate baseline at $76.7M | Correct problem size | CFO time | FY2027 planning | Threshold-sensitive |
| 05 | Fix three data defects | Unblocks 01 and 04 | Data owner time | Ongoing | Verified |
| X | FAR retention programme | Do not fund | $0 | n/a | Not identified |

Ordered by speed to a measurable result, not by dollar size.

**Exposure addressed is not cash saved.** We deliberately convert nothing into a
savings promise, because none of these has been tested at NovaCorp.

**The closing frame.** The FY2025 report says "budgets have been put aside to
support a programme for People Reinvention" three times, always without a
figure, while every other initiative carries one. The final slide fills that
blank as a priority order: Disengagement $61.8M, Entity_C window $18.6M,
Regrettable exits $12.5M, Agency $2.4M.

---

## 10. Open items

| Item | Impact | Owner |
|---|---|---|
| The attrition log reconciles to 60% of reported FY2025 departures | Every attrition cost stays a floor | unresolved |
| Disengagement threshold differs between our work and the parallel deck (68.8%/4.5% vs 38.3%/5.6%) | Two artefacts quote different numbers for the same thing | needs one definition before submission |
| New starters excluded from the early-warning estimate | Highest-risk group is unmeasured | future work |
| Manager finding not controlled for team context | Constrains the recommendation to a diagnostic | future work |

---

## 11. Ethics and responsible practice

- **No individual is labelled a flight risk.** Cohorts are a screen for a human
  conversation; managers and HR make the judgement.
- **No automated employment decision** is recommended anywhere.
- **Demographic fields are not used** to rank, predict or prioritise
  individuals.
- **Causal language is used only where a design supports it**, which in this
  project is nowhere. Every relationship is stated as association.
- **Every threshold we chose is sensitivity-tested and published**, so a reader
  can see the answer under alternatives we did not pick.
- **Exit reasons are treated as directional**, since the brief notes 40 to 60%
  do not reflect the primary driver.
- **Rejected hypotheses are reported**, not dropped. Two of three mechanisms did
  not survive and both appear in the deck.

---

## 12. Reproducing everything

```powershell
cd D:\Novacorp\GitHappens_AccentureXUSYDDatathon
python src\run_pipeline.py Accenture_Case_Comp_Data.zip   # rebuild the cache
python tools\run_notebooks.py                             # run all six notebooks
start dashboard\index.html                                # open the dashboard
```

Every figure in the deck traces to a notebook section. The mapping is in
appendix A1 of the deck and in `FUNCTIONS.md`.
