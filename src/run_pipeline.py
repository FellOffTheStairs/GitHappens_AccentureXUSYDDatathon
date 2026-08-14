"""
NovaCorp pipeline runner — rebuilds the parquet cache from the raw data.

    python src/run_pipeline.py Accenture_Case_Comp_Data.zip
    python src/run_pipeline.py <folder> --outdir clean

Produces exactly what notebooks/01_ingest_clean.ipynb produces, and the rest of
the notebooks read the output either way:

    clean/employees_clean.parquet     the four source tables, types coerced
    clean/attrition_clean.parquet
    clean/engagement_clean.parquet
    clean/performance_clean.parquet
    clean/analysis_df.parquet         one row per employee, all features  <- main artefact
    clean/engagement_long.parquet     one row per employee-wave, for time series
    clean/monthly_exits.parquet       monthly exit counts, for the FAR event study
    clean/data_quality.csv            column-level profile

The *analysis* lives in the notebooks. This is here so the cache can be rebuilt
in one command — from a terminal, a fresh clone, or CI — without opening
Jupyter. If you want the findings, run the notebooks.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

import etl


def banner(text: str) -> None:
    print("\n" + "=" * 74)
    print(text)
    print("=" * 74)


def save(frame: pd.DataFrame, stem: str, outdir: Path) -> None:
    """Parquet preserves dtypes and reloads fast. Falls back to CSV if no
    parquet engine is installed."""
    try:
        frame.to_parquet(outdir / f"{stem}.parquet", index=False)
        suffix = "parquet"
    except (ImportError, ValueError):
        frame.to_csv(outdir / f"{stem}.csv", index=False)
        suffix = "csv  (pip install pyarrow for parquet)"
    print(f"  {stem:<20} {frame.shape[0]:>7,} rows x {frame.shape[1]:>3} cols   {suffix}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("source", help="path to the data zip or an extracted folder")
    ap.add_argument("--outdir", default="clean", help="where to write the cache")
    args = ap.parse_args()

    banner("INGEST")
    raw = etl.load_raw(args.source)
    if len(raw) < 4:
        print(f"\n  Only found {sorted(raw)}. Fix the source path before continuing.")
        return 1

    clean = etl.clean_all(raw)

    banner("DATA QUALITY PROFILE")
    dq = pd.concat(
        [etl.profile(clean[k], k) for k in
         ["employees", "attrition", "engagement", "performance"]],
        ignore_index=True,
    )

    etl.reconcile(clean["employees"], clean["attrition"])

    banner("BUILD")
    df = etl.build_analysis_df(clean)
    eng_long = etl.engagement_long(clean, df)
    monthly = etl.monthly_exits(df)

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    for key, stem in [("employees", "employees_clean"), ("attrition", "attrition_clean"),
                      ("engagement", "engagement_clean"), ("performance", "performance_clean")]:
        save(clean[key], stem, outdir)
    save(df, "analysis_df", outdir)
    save(eng_long, "engagement_long", outdir)
    save(monthly, "monthly_exits", outdir)

    dq.to_csv(outdir / "data_quality.csv", index=False)
    print(f"  {'data_quality.csv':<20} {len(dq):>7,} columns profiled")

    banner(f"WRITTEN TO {outdir.resolve()}")
    print("\n  Next: open notebooks/02_data_quality.ipynb — the reconciliation above does not agree with the annual report, and that is the point of interest.")
    return 0


if __name__ == "__main__":
    sys.exit(main())