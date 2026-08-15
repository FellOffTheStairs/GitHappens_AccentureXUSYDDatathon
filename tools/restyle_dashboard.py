"""
Apply the four-colour system and layout refinements to dashboard/index.html.

    python tools/restyle_dashboard.py

Content is untouched. This only rewrites the CSS token block, remaps the old
five-colour semantics onto four hues, adds a spacing scale and print styles,
and clears em dashes from the page prose.

Idempotent: running it twice changes nothing the second time.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "dashboard" / "index.html"
EM = "\u2014"

# --------------------------------------------------------------------------
# The palette. Four hues, each with a fill value and a darker ink value for
# small text. Light-mode ink variants clear 4.5:1 on the card surface; fills
# clear the 3:1 graphical threshold. Dark-mode values clear both at once.
#
#   accent   blue     reference, published figure, a claim that is identified
#   counter  orange   observed value, the thing that differs from reference
#   flag     amber    partial confidence, a floor, a caution
#   stop     red      do not do this, not identified
#
# Everything else is the neutral ink scale. No fifth hue.
# --------------------------------------------------------------------------

TOKENS_LIGHT = """:root {
  /* surfaces and ink */
  --paper:      #f4f3ee;
  --card:       #fcfcfb;
  --sunk:       #f7f6f1;
  --ink:        #0b0b0b;
  --ink-2:      #52514e;
  --ink-3:      #86847e;
  --rule:       #e1e0d9;
  --rule-soft:  #edece6;

  /* four hues: fill, then ink for small text */
  --accent:      #2a78d6;
  --accent-ink:  #1f5fae;
  --accent-wash: #e8f0fc;
  --counter:     #e2683a;
  --counter-ink: #a8460f;
  --flag:        #c98a10;
  --flag-ink:    #8a5600;
  --stop:        #d03b3b;
  --stop-ink:    #b02525;

  --shadow: 0 1px 2px rgba(11,11,11,.05), 0 8px 24px -16px rgba(11,11,11,.28);

  /* spacing scale, 4px base */
  --s1: 4px;  --s2: 8px;  --s3: 12px; --s4: 16px;
  --s5: 22px; --s6: 30px; --s7: 40px;
  --radius: 4px;

  --sans: "Segoe UI", -apple-system, BlinkMacSystemFont, "Helvetica Neue", Arial, sans-serif;
  --serif: Georgia, "Iowan Old Style", "Palatino Linotype", "Times New Roman", serif;
  --mono: Consolas, ui-monospace, "SF Mono", "Cascadia Mono", Menlo, monospace;
}"""

DARK_BODY = """  --paper:      #121110;
  --card:       #1c1b19;
  --sunk:       #201e1b;
  --ink:        #f2f1ec;
  --ink-2:      #b0aea8;
  --ink-3:      #86847e;
  --rule:       #302e2a;
  --rule-soft:  #26241f;

  --accent:      #5b9df0;
  --accent-ink:  #8bbaf5;
  --accent-wash: #1d2b3d;
  --counter:     #f0824f;
  --counter-ink: #f5a077;
  --flag:        #e0a53c;
  --flag-ink:    #ecc274;
  --stop:        #f06a6a;
  --stop-ink:    #f59191;

  --shadow: 0 1px 2px rgba(0,0,0,.4), 0 8px 24px -16px rgba(0,0,0,.8);"""

TOKENS_DARK_MEDIA = (
    "@media (prefers-color-scheme: dark) {\n"
    '  :root:not([data-theme="light"]) {\n'
    + "\n".join("  " + line for line in DARK_BODY.split("\n"))
    + "\n  }\n}"
)

TOKENS_DARK_ATTR = ':root[data-theme="dark"] {\n' + DARK_BODY + "\n}"

HEADER_COMMENT = """/* ─────────────────────────────────────────────────────────────
   Tokens.

   Four hues carry every meaning on the page:
     accent  blue    reference / published / identified
     counter orange  observed / the value that differs
     flag    amber   partial confidence / a floor / caution
     stop    red     do not do this / not identified

   Each has a -ink variant for small text (4.5:1 on the card
   surface) and the fills clear 3:1. Everything else is the
   neutral scale. Adding a fifth hue means one of these has
   stopped carrying its meaning; fix that instead.

   Series hues match src/nbinit.py, so a colour means the same
   thing here as on the deck figures.
   ───────────────────────────────────────────────────────────── */"""

# Old five-colour semantics onto the four hues. Green is gone: a claim that is
# well supported is drawn in the reference colour, because that is what it is.
REMAP = [
    ("var(--good)", "var(--accent-ink)"),
    ("var(--warn)", "var(--flag-ink)"),
    ("var(--crit)", "var(--stop-ink)"),
    ("var(--stamp-bg)", "var(--sunk)"),
    (".stamp.is-solid  { color: var(--accent-ink); }",
     ".stamp.is-solid { color: var(--accent-ink); background: var(--accent-wash); }"),
    (".stamp.is-floor  { color: var(--flag-ink); }",
     ".stamp.is-floor { color: var(--flag-ink); }"),
    (".stamp.is-none   { color: var(--stop-ink); }",
     ".stamp.is-none { color: var(--stop-ink); }"),
    (".meta-value.good { color: var(--accent-ink); }",
     ".meta-value.good { color: var(--accent-ink); }"),
    ('.bar-fill.pub  { background: var(--accent); }',
     '.bar-fill.pub { background: var(--accent); }'),
]

# Component refinements appended after the existing rules so they win on order.
EXTRA_CSS = """
/* ── Refinements ──────────────────────────────────────────── */

/* Verdict gets a coloured rule so the confidence grade is legible from the
   scroll position, not just from the stamp text. */
.verdict { border-left: 3px solid var(--rule); padding-left: var(--s5); }
.verdict:has(.is-solid) { border-left-color: var(--accent); }
.verdict:has(.is-floor) { border-left-color: var(--flag); }
.verdict:has(.is-none)  { border-left-color: var(--stop); }

.stamp { background: var(--sunk); border-color: currentColor; }

/* KPI: the first cell of each row is the reference figure, so tint it. */
.kpi { transition: background .15s; }
.kpi:hover { background: var(--sunk); }
.kpi-value { font-variant-numeric: tabular-nums; }

/* Cards lift slightly on hover so the grid reads as separable objects. */
.card { transition: border-color .15s, transform .15s; }
.card:hover { border-color: var(--ink-3); }

/* Bars: rounded on both ends, and a track behind them so short bars still
   show their scale. */
.bar-fill { border-radius: 2px; }
.bar-fill.pub { background: var(--accent); }
.bar-fill.obs { background: var(--counter); }
.bar-fill.solo { background: var(--accent); }
.bar-fill.mute { background: var(--ink-3); opacity: .38; }
.stack .seg-both { background: var(--accent); }
.stack .seg-missed { background: var(--counter); }
.stack .seg-only { background: var(--ink-3); opacity: .38; }
.sw-pub { background: var(--accent); }
.sw-obs { background: var(--counter); }

/* Callouts inherit the same four meanings. */
.callout.is-warn { border-left-color: var(--flag); }
.callout.is-crit { border-left-color: var(--stop); }
.rec.is-dont { border-left-color: var(--stop); }
.caveat-tag { color: var(--flag-ink); border-color: var(--flag); }

/* Sidebar active row reads as a selected tab, not a hover. */
.tab[aria-selected="true"] { background: var(--accent-wash); }

/* Visible focus everywhere, for keyboard and for a live demo on a big screen. */
a:focus-visible, button:focus-visible {
  outline: 2px solid var(--accent); outline-offset: 2px; border-radius: 2px;
}

/* Print: flatten to light, show every screen, drop the chrome. Useful for
   dropping a screen into the appendix as a PDF page. */
@media print {
  :root, :root[data-theme="dark"] {
    --paper: #fff; --card: #fff; --sunk: #f6f6f4;
    --ink: #000; --ink-2: #333; --ink-3: #666;
    --rule: #ccc; --rule-soft: #e4e4e0; --shadow: none;
    --accent: #1f5fae; --accent-ink: #1f5fae; --accent-wash: #eef3fb;
    --counter: #a8460f; --counter-ink: #a8460f;
    --flag: #8a5600; --flag-ink: #8a5600;
    --stop: #b02525; --stop-ink: #b02525;
  }
  .sidebar, .theme-toggle { display: none; }
  .shell, .content { display: block; max-width: none; padding: 0; }
  .screen[hidden] { display: block !important; }
  .screen { break-before: page; }
  .card, .rec { break-inside: avoid; box-shadow: none; }
}
"""


def main() -> int:
    if not PAGE.exists():
        print(f"  {PAGE} not found")
        return 1

    html = PAGE.read_text(encoding="utf-8")
    before = html

    if "--accent-ink" in html:
        print("  Already restyled. Nothing to do.")
        return 0

    # 1. Header comment.
    html = re.sub(
        r"/\* ─{10,}.*?─{10,} \*/",
        HEADER_COMMENT,
        html,
        count=1,
        flags=re.S,
    )

    # 2. Token blocks.
    html = re.sub(r":root \{.*?\n\}", TOKENS_LIGHT, html, count=1, flags=re.S)
    html = re.sub(
        r"@media \(prefers-color-scheme: dark\) \{.*?\n  \}\n\}",
        TOKENS_DARK_MEDIA,
        html,
        count=1,
        flags=re.S,
    )
    html = re.sub(
        r':root\[data-theme="dark"\] \{.*?\n\}',
        TOKENS_DARK_ATTR,
        html,
        count=1,
        flags=re.S,
    )

    # 3. Remap the retired tokens.
    for old, new in REMAP:
        html = html.replace(old, new)

    # 4. Append refinements just before the closing style tag.
    html = html.replace("</style>", EXTRA_CSS + "\n</style>", 1)

    # 5. Em dashes out of the page prose.
    dashes = html.count(EM)
    html = re.sub(r" " + EM + r" ", ", ", html)
    html = html.replace(EM, ",")

    PAGE.write_text(html, encoding="utf-8")

    leftover = [t for t in ("--good", "--warn:", "--crit:") if t in html]
    print(f"  restyled  {PAGE.relative_to(ROOT)}")
    print(f"  {dashes} em dashes removed")
    print(f"  retired tokens still present: {leftover or 'none'}")
    print(f"  {len(before):,} -> {len(html):,} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
