"""
Add the round 3 findings to the dashboard, and raise its visual density.

    python tools/patch_dashboard_r3.py

Four additions, each replacing prose or a table with a drawn chart:

  A1  the channel null result, as a small-multiple comparison
  A1  the sensitivity table gains a heat tint so the shape is visible
  A2  the integration curve, the new forward-looking finding
  REC an allocation chart for the People Reinvention budget

Every chart is inline SVG using the existing four tokens. No new colours, no
external requests. Idempotent.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "dashboard" / "index.html"


# --------------------------------------------------------------------------
# CSS for the new components
# --------------------------------------------------------------------------

CSS = """
/* ── Round 3 components ───────────────────────────────────── */

/* Heat tint on a numeric table. One hue, opacity carries magnitude, and the
   number stays readable because the tint sits behind it. */
td.heat { position: relative; }
td.heat::before {
  content: ""; position: absolute; inset: 2px; border-radius: 2px;
  background: var(--counter); opacity: calc(var(--v) * 0.42); z-index: 0;
}
td.heat > span { position: relative; z-index: 1; }

/* Small multiples: one mini bar per channel, shared scale, direct labels. */
.multiples {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(126px, 1fr));
  gap: 1px; background: var(--rule); border: 1px solid var(--rule);
  border-radius: var(--radius); overflow: hidden;
}
.mult { background: var(--card); padding: var(--s3) var(--s4) var(--s4); }
.mult-name {
  font-size: 11.5px; color: var(--ink-3); text-transform: uppercase;
  letter-spacing: .05em; margin-bottom: var(--s2);
}
.mult-row { display: flex; align-items: center; gap: var(--s2); margin-bottom: 5px; }
.mult-bar { height: 9px; border-radius: 2px; background: var(--ink-3); opacity: .4; }
.mult-bar.is-focus { background: var(--counter); opacity: 1; }
.mult-val {
  font-size: 11.5px; color: var(--ink-2); font-variant-numeric: tabular-nums;
  white-space: nowrap;
}
.mult.is-focus { background: var(--sunk); }
.mult.is-focus .mult-name { color: var(--counter-ink); }

/* Allocation bar: one row, segments sized by share, labels underneath. */
.alloc { display: flex; height: 34px; gap: 2px; margin-bottom: var(--s3); }
.alloc span {
  display: flex; align-items: center; justify-content: center;
  font-size: 12px; font-weight: 600; color: #fff; border-radius: 2px;
}
.alloc-key { display: flex; flex-wrap: wrap; gap: var(--s4); font-size: 12.5px; }
.alloc-key span { display: inline-flex; align-items: center; gap: 7px; color: var(--ink-2); }
"""


# --------------------------------------------------------------------------
# A2: the integration curve
# --------------------------------------------------------------------------

# Plot geometry: x from month 3 to 24, y from 0 to 16 percent.
def px(month: float) -> float:
    return 70 + (month - 3) * (600 - 70) / (24 - 3)


def py(pct: float) -> float:
    return 214 - pct * (214 - 34) / 16


def path_for(points: list[tuple[float, float]]) -> str:
    return " ".join(f"{px(m):.0f},{py(v):.0f}" for m, v in points)


ENTITY_A = [(3, 0.0), (6, 0.1), (9, 0.5), (12, 1.7), (18, 4.2), (24, 6.2)]
ENTITY_B = [(3, 6.0), (6, 8.3), (9, 10.2), (12, 12.3), (18, 15.5)]
ENTITY_C = [(3, 8.1), (6, 9.1)]
ORIGIN = [(3, 0.2), (6, 0.2), (9, 0.2), (12, 0.2), (18, 0.3), (24, 0.3)]

CURVE_CARD = f"""
  <div class="section-rule"><h3>The integration curve</h3></div>

  <div class="card">
    <h3>Entity_C is tracking Entity_B, not Entity_A</h3>
    <p class="sub">Share of each acquisition cohort that had left by month H,
      counting only employees observed at least that long. Cohorts joined in
      different years, so a raw comparison would measure exposure rather than
      attrition. Lines stop where a cohort runs out of observation.</p>

    <svg class="chart" viewBox="0 0 660 268" role="img"
      aria-label="Integration attrition by cohort. At six months Entity_A had lost 0.1 percent, Entity_B 8.3 percent and Entity_C 9.1 percent. Entity_C is following Entity_B's path.">
      <g>
        <line class="grid-line" x1="70" y1="{py(0):.0f}" x2="620" y2="{py(0):.0f}"></line>
        <line class="grid-line" x1="70" y1="{py(4):.0f}" x2="620" y2="{py(4):.0f}"></line>
        <line class="grid-line" x1="70" y1="{py(8):.0f}" x2="620" y2="{py(8):.0f}"></line>
        <line class="grid-line" x1="70" y1="{py(12):.0f}" x2="620" y2="{py(12):.0f}"></line>
        <line class="grid-line" x1="70" y1="{py(16):.0f}" x2="620" y2="{py(16):.0f}"></line>
        <text class="axis-text" x="60" y="{py(0)+4:.0f}" text-anchor="end">0%</text>
        <text class="axis-text" x="60" y="{py(4)+4:.0f}" text-anchor="end">4%</text>
        <text class="axis-text" x="60" y="{py(8)+4:.0f}" text-anchor="end">8%</text>
        <text class="axis-text" x="60" y="{py(12)+4:.0f}" text-anchor="end">12%</text>
        <text class="axis-text" x="60" y="{py(16)+4:.0f}" text-anchor="end">16%</text>
      </g>

      <!-- six month marker: the only horizon every cohort supports -->
      <line x1="{px(6):.0f}" y1="28" x2="{px(6):.0f}" y2="220"
            stroke="var(--ink-3)" stroke-width="1" stroke-dasharray="3 3"></line>
      <text class="axis-text" x="{px(6)+6:.0f}" y="30">like-for-like horizon</text>

      <polyline fill="none" stroke="var(--ink-3)" stroke-width="1.6"
                stroke-dasharray="4 3" points="{path_for(ORIGIN)}"></polyline>
      <polyline fill="none" stroke="var(--accent)" stroke-width="2.4"
                points="{path_for(ENTITY_A)}"></polyline>
      <polyline fill="none" stroke="var(--counter)" stroke-width="2.4"
                points="{path_for(ENTITY_B)}"></polyline>
      <polyline fill="none" stroke="var(--stop)" stroke-width="3"
                points="{path_for(ENTITY_C)}"></polyline>

      <g fill="var(--accent)">{"".join(f'<circle cx="{px(m):.0f}" cy="{py(v):.0f}" r="3.5"></circle>' for m, v in ENTITY_A)}</g>
      <g fill="var(--counter)">{"".join(f'<circle cx="{px(m):.0f}" cy="{py(v):.0f}" r="3.5"></circle>' for m, v in ENTITY_B)}</g>
      <g fill="var(--stop)">{"".join(f'<circle cx="{px(m):.0f}" cy="{py(v):.0f}" r="4.5"></circle>' for m, v in ENTITY_C)}</g>

      <text class="series-label" x="{px(18)+8:.0f}" y="{py(4.2)+4:.0f}" fill="var(--accent)">Entity_A · 2023</text>
      <text class="series-label" x="{px(18)+8:.0f}" y="{py(15.5)+4:.0f}" fill="var(--counter)">Entity_B · 2024</text>
      <text class="series-label" x="{px(6)+10:.0f}" y="{py(9.1)-8:.0f}" fill="var(--stop)">Entity_C · 2025</text>
      <text class="axis-text" x="{px(12):.0f}" y="{py(0.3)-6:.0f}" fill="var(--ink-3)">NovaCorp-Origin</text>

      <g>
        <text class="axis-text" x="{px(3):.0f}" y="234" text-anchor="middle">3</text>
        <text class="axis-text" x="{px(6):.0f}" y="234" text-anchor="middle">6</text>
        <text class="axis-text" x="{px(9):.0f}" y="234" text-anchor="middle">9</text>
        <text class="axis-text" x="{px(12):.0f}" y="234" text-anchor="middle">12</text>
        <text class="axis-text" x="{px(18):.0f}" y="234" text-anchor="middle">18</text>
        <text class="axis-text" x="{px(24):.0f}" y="234" text-anchor="middle">24</text>
        <text class="axis-text" x="345" y="256" text-anchor="middle"
              style="fill:var(--ink-3)">months since joining NovaCorp</text>
      </g>
    </svg>

    <p class="footnote"><b>At six months: Entity_A 0.1%, Entity_B 8.3%,
      Entity_C 9.1%.</b> One departure in 1,950 people against 156 in 1,884 and
      92 in 1,014. Entity_A's integration was not merely better, it was almost
      flawless for two quarters, and whatever produced that was not repeated.
      Entity_C is about eight months in and still inside its risk window.</p>
  </div>
"""

FORECAST_CARD = """
  <div class="grid two" style="margin-top:18px">
    <div class="card">
      <h3>What the curve implies for the 1,014 people in Entity_C</h3>
      <p class="sub">Projecting the cohort forward along each of the two paths
        already observed inside this company, at Finance's own replacement cost.</p>
      <div class="bars">
        <div class="bar-row">
          <div class="bar-name">Departed already<small>month 6, observed</small></div>
          <div class="bar-line"><div class="bar-fill mute" style="width:58.6%"></div><span class="bar-val"><b>92</b> people</span></div>
        </div>
        <div class="bar-row">
          <div class="bar-name">If it follows Entity_A<small>4.2% by month 18</small></div>
          <div class="bar-line"><div class="bar-fill solo" style="width:27.4%"></div><span class="bar-val"><b>43</b> total · $7.0M</span></div>
        </div>
        <div class="bar-row">
          <div class="bar-name">If it follows Entity_B<small>15.5% by month 18</small></div>
          <div class="bar-line"><div class="bar-fill obs" style="width:100%"></div><span class="bar-val"><b>157</b> total · $25.6M</span></div>
        </div>
      </div>
      <p class="footnote"><b>$18.6M sits between the two paths.</b> This is the
        only forward-looking number in the analysis: every other finding
        describes something that has already happened. It concerns a named
        cohort with a date attached, and the window has not closed.</p>
    </div>

    <div class="card">
      <h3>What it is and is not</h3>
      <p class="sub">The comparison is corrected for exposure. It is not a
        controlled design, and the deck should say so before a judge does.</p>
      <p class="callout"><b>It is like-for-like.</b> Each cohort is measured at
        the same horizon, counting only people observed that long. This is the
        same correction the FAR event study needed, and without it Entity_C
        looks catastrophic purely because it is new.</p>
      <p class="callout is-warn"><b>It is association, not proof.</b> The three
        cohorts differ in size, sector mix and integration year. Nothing here
        isolates a cause, and Entity_C has only two points on the curve.</p>
      <p class="callout"><b>It is still the most actionable thing here.</b>
        Unlike the FAR hypothesis, which is unidentifiable in either direction,
        this is a live risk on 1,014 identified people. The CHRO can change the
        outcome; that is what separates it from the rest of the deck.</p>
    </div>
  </div>
"""


# --------------------------------------------------------------------------
# A1: the channel null result
# --------------------------------------------------------------------------

CHANNELS = [
    ("Agency", 52.5, 9.8, 10.4, True),
    ("Direct", 51.4, 9.9, 12.0, False),
    ("Referral", 52.1, 9.7, 12.2, False),
    ("Acquisition", 51.8, 10.9, 10.5, False),
    ("Graduate", 51.3, 13.8, 10.6, False),
]


def channel_block(name, fill, attr, reg, focus):
    f = " is-focus" if focus else ""
    return f"""      <div class="mult{f}">
        <div class="mult-name">{name}</div>
        <div class="mult-row"><div class="mult-bar{f}" style="width:{fill / 60 * 100:.0f}%"></div><span class="mult-val">{fill} d</span></div>
        <div class="mult-row"><div class="mult-bar{f}" style="width:{attr / 16 * 100:.0f}%"></div><span class="mult-val">{attr}%</span></div>
        <div class="mult-row"><div class="mult-bar{f}" style="width:{reg / 16 * 100:.0f}%"></div><span class="mult-val">{reg}%</span></div>
      </div>"""


NULL_CARD = f"""
  <div class="section-rule"><h3>A component that does not survive its own definition</h3></div>

  <div class="card">
    <h3>Finance calls it hiring inefficiency. Neither half of that is visible.</h3>
    <p class="sub">The brief defines this component as the cost premium of agency
      hiring <i>and poor-match early attrition</i>. Both halves are testable.
      Each channel below shows days to fill, attrition rate, and the share of its
      exits flagged regrettable, on a shared scale.</p>

    <div class="multiples">
{chr(10).join(channel_block(*c) for c in CHANNELS)}
    </div>

    <p class="footnote"><b>Agency is mid-pack or better on every dimension.</b>
      It fills roles 1.2 days slower than the fastest channel, leaves at a rate
      inside the range set by the other four, and its exits are <i>less</i>
      likely to be flagged regrettable than those of direct hires. The $2.4M is
      an agency spend figure, not an inefficiency figure. The 18% fee is also
      Finance's assumption: no cost, fee or cost-per-hire column exists in any of
      the four files, so nothing in this component is data-derived except the
      headcount. The label is kept because it is Finance's own taxonomy; the
      claim behind it is marked unevidenced.</p>
  </div>
"""


# --------------------------------------------------------------------------
# REC: the People Reinvention allocation
# --------------------------------------------------------------------------

ALLOC_CARD = """
  <div class="section-rule"><h3>The blank on page 8</h3></div>

  <div class="card">
    <h3>Every initiative in the FY2025 report carries a number. One does not.</h3>
    <p class="sub">"Budgets have been put aside to support a programme for People
      Reinvention" appears three times in the annual report, always without a
      figure, while $85M in synergies, $320M in technology and $40 to 50M in
      integration all carry one. This is the allocation that fills it.</p>

    <div class="alloc">
      <span style="flex:62;background:var(--counter)">Disengagement · $61.8M</span>
      <span style="flex:19;background:var(--stop)">Entity_C window · $18.6M</span>
      <span style="flex:12;background:var(--accent)">Regrettable · $12.5M</span>
      <span style="flex:2;background:var(--ink-3)"></span>
    </div>
    <div class="alloc-key">
      <span><i class="swatch" style="background:var(--counter)"></i> Measured and unaddressed, 4.1× Finance's assumption</span>
      <span><i class="swatch" style="background:var(--stop)"></i> Forward-looking, window still open</span>
      <span><i class="swatch" style="background:var(--accent)"></i> Already inside Finance's range</span>
      <span><i class="swatch" style="background:var(--ink-3)"></i> Agency spend, $2.4M</span>
    </div>

    <p class="footnote"><b>Read it as a priority order, not a budget request.</b>
      Two thirds of the addressable cost sits in a population nobody is currently
      measuring, and the cheapest instrument for finding them already exists in
      the engagement platform. The Entity_C segment is the only one with a
      deadline attached.</p>
  </div>
"""


def main() -> int:
    html = PAGE.read_text(encoding="utf-8")
    if "Round 3 components" in html:
        print("  Already applied.")
        return 0

    html = html.replace("</style>", CSS + "\n</style>", 1)

    # A1: null result before the "what to defend" rule.
    anchor = '  <div class="section-rule"><h3>What to defend, and what to concede</h3></div>'
    if anchor not in html:
        print("  A1 anchor not found")
        return 1
    html = html.replace(anchor, NULL_CARD + "\n" + anchor, 1)

    # A2: curve and forecast before the "distinction that matters" rule.
    anchor = '  <div class="section-rule"><h3>The distinction that matters</h3></div>'
    if anchor not in html:
        print("  A2 anchor not found")
        return 1
    html = html.replace(anchor, CURVE_CARD + FORECAST_CARD + "\n" + anchor, 1)

    # REC: allocation before the closing line.
    anchor = '  <div class="section-rule"><h3>If the board hears one sentence</h3></div>'
    if anchor not in html:
        print("  REC anchor not found")
        return 1
    html = html.replace(anchor, ALLOC_CARD + "\n" + anchor, 1)

    # Heat tint on the sensitivity table.
    tint = [
        ("<td>$28.1M</td><td>$17.1M</td><td>$10.9M</td>", [28.1, 17.1, 10.9]),
        ("<td>$52.8M</td><td>$34.2M</td><td>$23.2M</td>", [52.8, 34.2, 23.2]),
        ("<td>$87.7M</td><td>$61.8M</td><td>$44.3M</td>", [87.7, 61.8, 44.3]),
        ("<td>$126.8M</td><td>$95.4M</td><td>$71.8M</td>", [126.8, 95.4, 71.8]),
        ("<td>$165.3M</td><td>$131.2M</td><td>$104.0M</td>", [165.3, 131.2, 104.0]),
    ]
    for old, vals in tint:
        cells = "".join(
            f'<td class="heat" style="--v:{v / 165.3:.2f}"><span>${v}M</span></td>'
            for v in vals
        )
        html = html.replace(old, cells, 1)

    # Closing sentence now carries the forward-looking finding.
    html = html.replace(
        "<b>The $42M is understated roughly threefold on Finance's own arithmetic, the regulatory explanation everyone expected does not survive the data, and the most predictive early-warning signal available is already sitting unused in the engagement platform.</b>",
        "<b>The $42M is not too small, it is pointed at the wrong component: two thirds of the addressable cost sits with people who have not left and are not being measured. The regulatory explanation everyone expected does not survive the data. And 1,014 people in Entity_C are eight months into the same curve that cost you Entity_B.</b>",
    )

    PAGE.write_text(html, encoding="utf-8")
    print(f"  4 cards added, sensitivity table tinted, closing line rewritten")
    print(f"  {len(html):,} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
