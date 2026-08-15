"""
Final dashboard pass before commit.

    python tools/patch_dashboard_r4.py

Three additions:

1. A1 gains the attrition reconciliation. The published 10.4% is reproducible
   from the data, and reproducing it shows what it actually counts.
2. A3 gains manager effectiveness: a large effect stated plainly, with the
   causal claim narrowed in the box beside it.
3. The recommendations screen gains a decision sequence chart. Not a 2x2:
   what to start, who owns it, and when the result becomes observable.

Idempotent.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "dashboard" / "index.html"

CSS = """
/* ── Round 4 components ───────────────────────────────────── */

/* Paired claim: what the evidence supports, and what it does not. The two
   sit side by side so the narrowing is read at the same time as the effect. */
.claim-pair { display: grid; gap: 1px; background: var(--rule);
  border: 1px solid var(--rule); border-radius: var(--radius); overflow: hidden; }
@media (min-width: 700px) { .claim-pair { grid-template-columns: 1fr 1fr; } }
.claim { background: var(--card); padding: var(--s4) var(--s5) var(--s5); }
.claim-tag {
  font-family: var(--mono); font-size: 10.5px; letter-spacing: .09em;
  text-transform: uppercase; margin-bottom: var(--s2);
}
.claim.is-yes .claim-tag { color: var(--accent-ink); }
.claim.is-no  .claim-tag { color: var(--flag-ink); }
.claim.is-no { background: var(--sunk); }
.claim p { margin: 0; font-size: 13.5px; line-height: 1.6; color: var(--ink-2); }
.claim p + p { margin-top: var(--s2); }
.claim b { color: var(--ink); }

/* Reconciliation ledger: a formula shown as its parts. */
.ledger { font-family: var(--mono); font-size: 13px; }
.ledger div {
  display: flex; justify-content: space-between; gap: var(--s4);
  padding: 7px 0; border-bottom: 1px solid var(--rule-soft);
}
.ledger div:last-child { border-bottom: 0; border-top: 1px solid var(--rule); font-weight: 600; }
.ledger .lbl { color: var(--ink-2); }
.ledger .val { color: var(--ink); font-variant-numeric: tabular-nums; white-space: nowrap; }

/* Decision sequence: rows of interventions against a shared timeline. */
.seq { display: flex; flex-direction: column; gap: 1px;
  background: var(--rule); border: 1px solid var(--rule);
  border-radius: var(--radius); overflow: hidden; }
.seq-head, .seq-row {
  display: grid; grid-template-columns: minmax(150px, 1.5fr) 3fr minmax(96px, .9fr);
  gap: var(--s4); background: var(--card); padding: var(--s3) var(--s4); align-items: center;
}
.seq-head { background: var(--sunk); }
.seq-head span {
  font-family: var(--mono); font-size: 10px; letter-spacing: .09em;
  text-transform: uppercase; color: var(--ink-3);
}
.seq-name { font-size: 13.5px; color: var(--ink); font-weight: 600; line-height: 1.3; }
.seq-name small { display: block; font-weight: 400; color: var(--ink-3); font-size: 11.5px; }
.seq-track { position: relative; height: 30px; }
.seq-track::before {
  content: ""; position: absolute; left: 0; right: 0; top: 14px;
  height: 1px; background: var(--rule);
}
.seq-bar {
  position: absolute; top: 9px; height: 11px; border-radius: 2px;
}
.seq-dot {
  position: absolute; top: 7px; width: 15px; height: 15px; border-radius: 50%;
  border: 2px solid var(--card); transform: translateX(-50%);
}
.seq-when {
  position: absolute; top: 24px; font-size: 10.5px; color: var(--ink-3);
  transform: translateX(-50%); white-space: nowrap;
}
.seq-val { font-size: 13px; color: var(--ink-2); text-align: right;
  font-variant-numeric: tabular-nums; }
.seq-val b { display: block; color: var(--ink); font-size: 14px; }
.seq-scale {
  display: grid; grid-template-columns: minmax(150px, 1.5fr) 3fr minmax(96px, .9fr);
  gap: var(--s4); padding: 6px var(--s4) 0;
  font-family: var(--mono); font-size: 10px; color: var(--ink-3);
  letter-spacing: .06em;
}
.seq-scale-inner { position: relative; height: 14px; }
.seq-scale-inner span { position: absolute; transform: translateX(-50%); }
"""

# --------------------------------------------------------------------------
# A1: the reconciliation
# --------------------------------------------------------------------------

RECON = """
  <div class="section-rule"><h3>The rate on page 8</h3></div>

  <div class="grid two">
    <div class="card">
      <h3>The published 10.4% is reproducible, and reproducing it is the finding</h3>
      <p class="sub">The FY2025 report gives voluntary attrition of 10.4% and a
        departmental breakdown. Both come out of this dataset exactly, using one
        formula, and the formula is not the one the label describes.</p>

      <div class="ledger">
        <div><span class="lbl">Full historical roster</span><span class="val">13,403</span></div>
        <div><span class="lbl">Still active</span><span class="val">12,003</span></div>
        <div><span class="lbl">Difference, all departures over 24 months</span><span class="val">1,400</span></div>
        <div><span class="lbl">1,400 ÷ 13,403</span><span class="val">10.4%</span></div>
      </div>

      <p class="footnote"><b>All seven departments reconcile to the decimal on the
        same formula.</b> Retail Banking 9.3%, Technology 10.4%, Risk &amp;
        Compliance 11.8%, Insurance 10.3%, Wealth Management 10.5%, Corporate
        Operations 11.6%, Executive Leadership 8.3%. There is no ambiguity about
        what was computed.</p>
    </div>

    <div class="card">
      <h3>Three things the label gets wrong</h3>
      <p class="sub">Each is independent of the others, and all three push the
        published figure in the same direction.</p>

      <div class="bars">
        <div class="bar-row">
          <div class="bar-name">Not voluntary<small>267 of the 1,400 are involuntary exits</small></div>
          <div class="bar-line"><div class="bar-fill mute" style="width:19%"></div><span class="bar-val">19% of the count</span></div>
        </div>
        <div class="bar-row">
          <div class="bar-name">Not annual<small>the window is 24 months, not 12</small></div>
          <div class="bar-line"><div class="bar-fill obs" style="width:100%"></div><span class="bar-val"><b>2×</b> overstatement</span></div>
        </div>
        <div class="bar-row">
          <div class="bar-name">Not headcount<small>denominator includes everyone who left</small></div>
          <div class="bar-line"><div class="bar-fill mute" style="width:12%"></div><span class="bar-val">13,403 vs 12,003</span></div>
        </div>
      </div>

      <p class="footnote"><b>Corrected, annual voluntary attrition is 4.7%.</b>
        1,133 voluntary exits over two years, against 12,003 active employees.
        Depending on which twelve months are chosen it runs between 4.6% and
        5.7%. Against AHRI's 15.2% Australian organisational average and ABS
        Financial and Insurance Services mobility of 7.9%, NovaCorp is not
        losing people quickly. It is losing them selectively.</p>
    </div>
  </div>

  <p class="callout" style="margin-top:18px"><b>This changes the target, not
    just the number.</b> FY2026 guidance sets voluntary attrition below 9.5%
    against a stated 10.4%. On a like-for-like basis the company is already at
    roughly half that, and has been for both years in the data. The scorecard is
    measuring a quantity that is not what its name says, which means the
    programme it governs could succeed or fail without the metric moving.</p>
"""

# --------------------------------------------------------------------------
# A3: manager effectiveness
# --------------------------------------------------------------------------

BANDS = [("4.0+", 4.5, 2874), ("3.5-4.0", 14.7, 2235), ("3.0-3.5", 27.0, 2256),
         ("2.5-3.0", 45.0, 1912), ("<2.5", 68.8, 1880)]


def band_row(label, pct, n):
    focus = "obs" if pct > 40 else "solo" if pct < 20 else "mute"
    return f"""        <div class="bar-row">
          <div class="bar-name">Manager rated {label}<small>n = {n:,}</small></div>
          <div class="bar-line"><div class="bar-fill {focus}" style="width:{pct / 68.8 * 100:.0f}%"></div><span class="bar-val"><b>{pct}%</b> persistently disengaged</span></div>
        </div>"""


MANAGER = f"""
  <div class="section-rule"><h3>What sits underneath the silence</h3></div>

  <div class="card">
    <h3>Manager effectiveness is the strongest signal in the survey, by a distance</h3>
    <p class="sub">Persistent disengagement, meaning a composite score below 3.0
      in two or more answered waves, plotted against the employee's mean rating
      of their manager. The gradient is monotonic across all five bands.</p>

    <div class="bars">
{chr(10).join(band_row(*b) for b in BANDS)}
    </div>

    <p class="footnote"><b>15.5× between the ends of the scale</b>, on 11,157
      employees with at least two answered waves. This is not a threshold
      artefact: disengagement falls at every step of the gradient, not only at
      the extremes.</p>
  </div>

  <div class="claim-pair" style="margin-top:18px">
    <div class="claim is-yes">
      <div class="claim-tag">What the evidence supports</div>
      <p><b>Employees who rate their manager poorly are far more likely to be
        persistently disengaged.</b> The association is large, monotonic and
        highly significant on a sample of 11,157.</p>
      <p>It is also the most controllable thing on these four screens. Manager
        capability is something NovaCorp already develops, and the next survey
        wave measures it directly.</p>
    </div>
    <div class="claim is-no">
      <div class="claim-tag">What it does not support</div>
      <p><b>It does not show that poor managers cause people to leave.</b>
        Manager rating correlates with attrition at r = -0.012 (p = 0.22), which
        is indistinguishable from zero. Disengagement itself correlates with
        attrition at r = -0.002.</p>
      <p>So the case for acting is a productivity and working-conditions case,
        not a retention case. Presenting it as an attrition programme would be
        claiming something these data do not show.</p>
    </div>
  </div>
"""

# --------------------------------------------------------------------------
# REC: the decision sequence
# --------------------------------------------------------------------------
# Timeline runs 0 to 12 months across the track.


def at(month):
    return f"{month / 12 * 100:.1f}%"


def bar(start, end, colour):
    return f'left:{start / 12 * 100:.1f}%;width:{(end - start) / 12 * 100:.1f}%;background:var(--{colour})'


SEQ_ROWS = [
    ("Manager effectiveness diagnostic",
     "CHRO, direct",
     bar(0, 3, "accent"), at(6), "accent",
     "Wave 6", "$61.8M", "exposure addressed"),
    ("Entity_C integration review",
     "CHRO with integration lead",
     bar(0, 2, "stop"), at(4), "stop",
     "month 4", "$18.6M", "between the two paths"),
    ("Non-response alert",
     "CHRO, no new data needed",
     bar(0, 1, "accent"), at(3), "accent",
     "next wave", "$1.8M", "at 20% retention"),
    ("Regrettable-exit definition",
     "CHRO with HR ops",
     bar(0, 1.5, "accent"), at(9), "accent",
     "next exit cycle", "$56.0M", "correctly scoped"),
    ("Cost baseline restatement",
     "CHRO with CFO",
     bar(1, 3, "flag"), at(3), "flag",
     "FY27 planning", "$76.7M", "restated from $42M"),
]


def seq_row(name, owner, barstyle, dot, colour, when, value, note):
    return f"""    <div class="seq-row">
      <div class="seq-name">{name}<small>{owner}</small></div>
      <div class="seq-track">
        <div class="seq-bar" style="{barstyle}"></div>
        <div class="seq-dot" style="left:{dot};background:var(--{colour})"></div>
        <div class="seq-when" style="left:{dot}">{when}</div>
      </div>
      <div class="seq-val"><b>{value}</b>{note}</div>
    </div>"""


SEQUENCE = f"""
  <div class="section-rule"><h3>What to start, and when you will know</h3></div>

  <div class="card">
    <h3>Ordered by when the result becomes observable, not by size</h3>
    <p class="sub">The bar is the work. The dot is the first point at which the
      data can tell you whether it worked. Everything here is inside twelve
      months and inside the CHRO's own authority, except the baseline
      restatement, which needs the CFO.</p>

    <div class="seq">
      <div class="seq-head">
        <span>Intervention</span><span>Work, then first measurable result</span><span>Exposure</span>
      </div>
{chr(10).join(seq_row(*r) for r in SEQ_ROWS)}
    </div>

    <div class="seq-scale">
      <span></span>
      <div class="seq-scale-inner">
        <span style="left:0">now</span>
        <span style="left:25%">3 months</span>
        <span style="left:50%">6 months</span>
        <span style="left:75%">9 months</span>
        <span style="left:100%">12 months</span>
      </div>
      <span></span>
    </div>

    <p class="footnote"><b>Two of these are time-bound and the rest are not.</b>
      The Entity_C window closes as that cohort passes its first year, and the
      non-response alert only fires if it exists before the next wave opens. The
      other three can start whenever there is capacity. Nothing here requires
      data NovaCorp does not already hold.</p>
  </div>
"""


def main() -> int:
    html = PAGE.read_text(encoding="utf-8")
    if "Round 4 components" in html:
        print("  Already applied.")
        return 0

    html = html.replace("</style>", CSS + "\n</style>", 1)

    targets = [
        ('  <div class="section-rule"><h3>A component that does not survive its own definition</h3></div>', RECON),
        ('  <div class="section-rule"><h3>The correction that makes it real</h3></div>', MANAGER),
        ('  <div class="section-rule"><h3>The blank on page 8</h3></div>', SEQUENCE),
    ]
    for anchor, block in targets:
        if anchor not in html:
            print(f"  anchor not found: {anchor[:60]}")
            return 1
        html = html.replace(anchor, block + "\n" + anchor, 1)

    PAGE.write_text(html, encoding="utf-8")
    print(f"  3 blocks added, {len(html):,} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
