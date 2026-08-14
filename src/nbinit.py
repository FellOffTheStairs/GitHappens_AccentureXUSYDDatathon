"""
Notebook bootstrap for the NovaCorp challenge.

Every notebook opens with the same four lines:

    %load_ext autoreload
    %autoreload 2
    import sys, pathlib
    _r = next(p for p in [pathlib.Path.cwd(), *pathlib.Path.cwd().parents]
              if (p / "src" / "etl.py").exists())
    sys.path.insert(0, str(_r / "src"))
    from nbinit import *

That gives you: `etl`, `pd`, `np`, `plt`, `sns`, the project paths, the chart
theme, and the cache helpers. Nothing else lives in the notebooks except the
analysis itself.

Keeping this in a module rather than in a cell means a fix here reaches all six
notebooks at once, and `%autoreload 2` picks it up without a kernel restart.
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

# Make `import etl` work no matter where the kernel was started from.
_SRC = Path(__file__).resolve().parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import etl  # noqa: E402


# --------------------------------------------------------------------------
# Paths - resolved from this file, so they hold whatever the kernel's cwd is
# --------------------------------------------------------------------------

ROOT = _SRC.parent
SRC = _SRC
NOTEBOOKS = ROOT / "notebooks"
CLEAN = ROOT / "clean"
FIGURES = ROOT / "figures"
DATA_ZIP = ROOT / "Accenture_Case_Comp_Data.zip"
DATA_EXTRACTED = ROOT / "extracted"

CLEAN.mkdir(exist_ok=True)
FIGURES.mkdir(exist_ok=True)

#: What 01_ingest_clean.ipynb writes and everything downstream reads.
CACHED_FRAMES = [
    "employees_clean",
    "attrition_clean",
    "engagement_clean",
    "performance_clean",
    "analysis_df",
    "engagement_long",
    "monthly_exits",
]


# --------------------------------------------------------------------------
# Chart theme
#
# Palette slots are assigned in a fixed order and never cycled - slot 1 is
# always the same hue in every notebook, so a colour means the same thing on
# every slide. Validated for colour-vision deficiency on the adjacent-pair
# gate; three slots (aqua, yellow, magenta) sit under 3:1 against the surface,
# so charts that use them carry direct labels rather than relying on the hue.
# --------------------------------------------------------------------------

SERIES = [
    "#2a78d6",  # 1 blue
    "#eb6834",  # 2 orange
    "#1baf7a",  # 3 aqua
    "#eda100",  # 4 yellow
    "#e87ba4",  # 5 magenta
    "#008300",  # 6 green
    "#4a3aa7",  # 7 violet
    "#e34948",  # 8 red
]

STATUS = {
    "good": "#0ca30c",
    "warning": "#fab219",
    "serious": "#ec835a",
    "critical": "#d03b3b",
}

INK = {
    "surface": "#fcfcfb",
    "primary": "#0b0b0b",
    "secondary": "#52514e",
    "muted": "#898781",
    "grid": "#e1e0d9",
    "axis": "#c3c2b7",
}

#: One-hue ramp for magnitude (heatmaps, choropleths). Light -> dark blue.
SEQ = LinearSegmentedColormap.from_list(
    "nova_seq",
    ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"],
)

#: Two hues either side of a neutral grey, for signed quantities.
DIV = LinearSegmentedColormap.from_list(
    "nova_div",
    ["#0d366b", "#3987e5", "#9ec5f4", "#f0efec", "#f0a6a6", "#e34948", "#8f1f1f"],
)


def apply_theme() -> None:
    """Recessive chrome, thin marks, no chartjunk. Called on import."""
    sns.set_theme(style="whitegrid")
    mpl.rcParams.update({
        "figure.figsize": (9, 5),
        "figure.dpi": 110,
        "savefig.dpi": 200,
        "savefig.bbox": "tight",
        "figure.facecolor": INK["surface"],
        "axes.facecolor": INK["surface"],
        "savefig.facecolor": INK["surface"],

        "font.family": "sans-serif",
        "font.sans-serif": ["Segoe UI", "DejaVu Sans", "sans-serif"],
        "font.size": 10,

        "axes.titlesize": 12,
        "axes.titleweight": "600",
        "axes.titlelocation": "left",
        "axes.titlepad": 12,
        "axes.labelsize": 10,
        "axes.labelcolor": INK["secondary"],
        "axes.edgecolor": INK["axis"],
        "axes.linewidth": 0.8,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.prop_cycle": mpl.cycler(color=SERIES),

        "grid.color": INK["grid"],
        "grid.linewidth": 0.8,
        "axes.grid.axis": "y",

        "xtick.color": INK["muted"],
        "ytick.color": INK["muted"],
        "xtick.labelcolor": INK["secondary"],
        "ytick.labelcolor": INK["secondary"],
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,

        "lines.linewidth": 2.0,
        "lines.markersize": 8,

        "legend.frameon": False,
        "legend.fontsize": 9,
    })


def figure(title: str, subtitle: str = "", figsize=(9, 5)):
    """A figure with the title block set the same way every time.

    Returns (fig, ax). The subtitle is where the 'so what' goes - a chart title
    that only names the axes is a wasted line.
    """
    fig, ax = plt.subplots(figsize=figsize)
    ax.set_title(title, color=INK["primary"])
    if subtitle:
        fig.text(0, 1.0, subtitle, ha="left", va="bottom",
                 fontsize=9.5, color=INK["secondary"], transform=ax.transAxes)
    return fig, ax


def save_fig(fig, name: str) -> Path:
    """Write to figures/ and report the path, so deck assets are never hunted for."""
    path = FIGURES / f"{name}.png"
    fig.savefig(path)
    print(f"  saved {path.relative_to(ROOT)}")
    return path


def label_bars(ax, fmt: str = "{:,.0f}", pad: int = 4, horizontal: bool = False) -> None:
    """Direct value labels on every bar container.

    Not decoration: three palette slots fall below the 3:1 contrast line, so
    charts using them owe the reader a label that does not depend on hue.
    """
    for container in ax.containers:
        ax.bar_label(
            container,
            fmt=lambda v: fmt.format(v),
            padding=pad,
            fontsize=9,
            color=INK["secondary"],
        )
    if horizontal:
        ax.margins(x=0.12)
    else:
        ax.margins(y=0.12)


# --------------------------------------------------------------------------
# Cache helpers - notebooks hand frames to each other through clean/
# --------------------------------------------------------------------------

def cache(df: pd.DataFrame, name: str) -> Path:
    """Write a frame to clean/<name>.parquet, dtypes intact."""
    path = CLEAN / f"{name}.parquet"
    df.to_parquet(path, index=False)
    print(f"  cached {name:<20} {df.shape[0]:>7,} rows x {df.shape[1]:>3} cols"
          f"  ({path.stat().st_size / 1e6:.1f} MB)")
    return path


def load(name: str) -> pd.DataFrame:
    """Read a frame written by 01_ingest_clean.ipynb."""
    path = CLEAN / f"{name}.parquet"
    if not path.exists():
        raise FileNotFoundError(
            f"{path.name} is missing - run notebooks/01_ingest_clean.ipynb first."
        )
    return pd.read_parquet(path)


def load_all() -> dict[str, pd.DataFrame]:
    """Every cached frame at once, for notebooks that need several."""
    return {n: load(n) for n in CACHED_FRAMES}


# --------------------------------------------------------------------------
# Small formatting helpers, so notebook cells stay about the analysis
# --------------------------------------------------------------------------

def millions(x: float) -> str:
    return f"${x / 1e6:,.1f}M"


def pct(x: float, dp: int = 1) -> str:
    return f"{100 * x:.{dp}f}%"


def rate_table(df: pd.DataFrame, by, target: str = "is_departed") -> pd.DataFrame:
    """n / events / rate, grouped by one or more columns. The shape most of the
    attrition questions in this case reduce to."""
    g = df.groupby(by, observed=True)[target]
    out = pd.DataFrame({"n": g.size(), "events": g.sum()})
    out["rate_pct"] = (100 * out["events"] / out["n"]).round(1)
    return out.sort_values("rate_pct", ascending=False)


def set_display() -> None:
    pd.set_option("display.max_columns", 60)
    pd.set_option("display.width", 160)
    pd.set_option("display.float_format", lambda v: f"{v:,.2f}")


apply_theme()
set_display()

__all__ = [
    "etl", "pd", "np", "plt", "sns", "mpl",
    "ROOT", "SRC", "NOTEBOOKS", "CLEAN", "FIGURES", "DATA_ZIP", "DATA_EXTRACTED",
    "CACHED_FRAMES",
    "SERIES", "STATUS", "INK", "SEQ", "DIV",
    "apply_theme", "figure", "save_fig", "label_bars",
    "cache", "load", "load_all",
    "millions", "pct", "rate_table", "set_display",
    "Patch", "Line2D", "Path",
]
