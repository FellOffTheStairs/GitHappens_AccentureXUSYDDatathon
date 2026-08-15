"""
Builds an analysis-ready employee-level dataframe from the four raw CSVs,
with derived features for three analysis angles:
  A1  $42M reconciliation      - implied vs actual headcount per cost component
  A2  FAR natural experiment   - staggered regulatory shock, Mar-2024 / Mar-2025
  A3  Non-response signal      - survey silence as a leading indicator of exit
"""

from __future__ import annotations

import re
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd


# Constants from the brief and the FY2025 annual report
OBS_START = pd.Timestamp("2024-01-01")
OBS_END = pd.Timestamp("2025-12-31")

# The window is 24 months. Finance's cost ranges are stated per year, so any
# count of events (exits, hires) has to be divided by this before the two are
# compared. Counts of people in a state (currently disengaged) are already
# annual and must not be divided.
OBS_YEARS = 2.0

# Finance benchmark constants (case brief, section 6)
REPLACEMENT_MULTIPLIER = 1.5      # x annual base salary
BACKFILL_RATE = 0.85              # share of vacated positions refilled
DISENGAGEMENT_LOSS = 0.15         # x base salary per year
SUPER_ONCOST = 0.120              # 12.0% legislated from 1 Jul 2025
AGENCY_FEE_RATE = 0.18            # x first-year base salary
DIRECT_HIRE_BENCHMARK = 5_500.0   # fully loaded, per hire

# Annual report FY2025 (year ended 30 Jun 2025)
AR_ACTIVE_HEADCOUNT = 12_003
AR_VOLUNTARY_ATTRITION = 0.104
AR_AVG_BASE_SALARY = 128_000.0
AR_SURVEY_RESPONSE_RATE = 0.817
AR_DEPARTURES_FY25 = 1_400

# Finance's published component ranges ($M)
COST_COMPONENTS = {
    "regrettable_attrition": (22e6, 25e6),
    "disengagement": (12e6, 15e6),
    "hiring_inefficiency": (4e6, 6e6),
}

# FAR commencement dates (APRA / ASIC, verified)
FAR_ADI = pd.Timestamp("2024-03-15")        # banking
FAR_INSURANCE_SUPER = pd.Timestamp("2025-03-15")  # insurance + superannuation

# Which NovaCorp departments sit under which FAR wave.
FAR_WAVE_MAP = {
    "Retail Banking": FAR_ADI,
    "Corporate Operations": FAR_ADI,
    "Technology": FAR_ADI,
    "Risk & Compliance": FAR_ADI,
    "Insurance": FAR_INSURANCE_SUPER,
    "Wealth Management": FAR_INSURANCE_SUPER,
}

# Culture Amp FS Australia benchmark tenure bands, for like-for-like comparison
TENURE_BINS = [-np.inf, 3, 6, 12, 24, 48, 72, 120, np.inf]
TENURE_LABELS = [
    "<3 months", "3-6 months", "6-12 months", "1-2 years",
    "2-4 years", "4-6 years", "6-10 years", "10+ years",
]

ENGAGEMENT_DIMENSIONS = [
    "manager_effectiveness", "psychological_safety", "recognition",
    "career_development", "senior_leadership_trust", "purpose_meaning",
    "wellbeing", "confidence_in_role_future",
]

# Filename variants seen across the brief, the induction slides and the repo
FILE_PATTERNS = {
    "employees": r"employee",
    "attrition": r"att?[ir]+ition",   # tolerates the 'attirition' typo
    "engagement": r"engage",
    "performance": r"perform",
}

# Ingest
def _is_junk(name: str) -> bool:
    """macOS archive artefacts and hidden files."""
    p = Path(name)
    return (
        "__MACOSX" in p.parts
        or "_MACOSX" in p.parts
        or p.name.startswith("._")
        or p.name.startswith(".")
    )

def discover(source: str | Path) -> dict[str, Path]:
    """Find the four CSVs in a directory or zip. Extracts zips to <parent>/extracted."""
    source = Path(source)

    if source.suffix.lower() == ".zip":
        dest = source.parent / "extracted"
        dest.mkdir(exist_ok=True)
        with zipfile.ZipFile(source) as zf:
            for member in zf.namelist():
                if not _is_junk(member) and not member.endswith("/"):
                    zf.extract(member, dest)
        search_root = dest
    else:
        search_root = source

    candidates = [p for p in search_root.rglob("*.csv") if not _is_junk(str(p))]

    found: dict[str, Path] = {}
    for key, pattern in FILE_PATTERNS.items():
        matches = [p for p in candidates if re.search(pattern, p.name, re.I)]
        if matches:
            # prefer the shallowest, shortest filename if several match
            found[key] = sorted(matches, key=lambda p: (len(p.parts), len(p.name)))[0]

    missing = set(FILE_PATTERNS) - set(found)
    if missing:
        print(f"  WARNING: could not locate {sorted(missing)}")
        print(f"  CSVs seen: {[p.name for p in candidates]}")

    return found


def load_raw(source: str | Path) -> dict[str, pd.DataFrame]:
    paths = discover(source)
    raw = {}
    for key, path in paths.items():
        df = pd.read_csv(path, low_memory=False)
        df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
        raw[key] = df
        print(f"  loaded {key:<12} {path.name:<28} {df.shape[0]:>7,} rows x {df.shape[1]:>2} cols")
    return raw


# Type coercion - production HR exports are messy by design here
_TRUE = {"true", "t", "yes", "y", "1", "1.0"}
_FALSE = {"false", "f", "no", "n", "0", "0.0"}


def to_bool(s: pd.Series) -> pd.Series:
    """Coerce mixed boolean representations to nullable boolean."""
    if s.dtype == bool:
        return s.astype("boolean")
    norm = s.astype("string").str.strip().str.lower()
    out = pd.Series(pd.NA, index=s.index, dtype="boolean")
    out[norm.isin(_TRUE)] = True
    out[norm.isin(_FALSE)] = False
    return out


def to_date(s: pd.Series) -> pd.Series:
    """Coerce dates, trying ISO first then dayfirst, since HRIS exports mix formats."""
    out = pd.to_datetime(s, errors="coerce", format="ISO8601")
    unparsed = out.isna() & s.notna()
    if unparsed.any():
        fallback = pd.to_datetime(s[unparsed], errors="coerce", dayfirst=True)
        out.loc[unparsed] = fallback
    return out


def to_num(s: pd.Series) -> pd.Series:
    """Strip currency symbols, commas and stray whitespace before numeric coercion."""
    if pd.api.types.is_numeric_dtype(s):
        return s
    cleaned = (
        s.astype("string")
        .str.replace(r"[$,\s]", "", regex=True)
        .str.replace(r"^\((.*)\)$", r"-\1", regex=True)  # (123) -> -123
    )
    return pd.to_numeric(cleaned, errors="coerce")


def norm_cat(s: pd.Series) -> pd.Series:
    """Trim and collapse internal whitespace. Deliberately does NOT change case:
    case variants are themselves a data quality finding worth reporting."""
    return s.astype("string").str.strip().str.replace(r"\s+", " ", regex=True)

def clean_frame(df: pd.DataFrame, spec: dict[str, str]) -> pd.DataFrame:
    """Apply a {column: kind} spec, skipping columns that are absent."""
    df = df.copy()
    fns = {"date": to_date, "bool": to_bool, "num": to_num, "cat": norm_cat}
    for col, kind in spec.items():
        if col in df.columns:
            df[col] = fns[kind](df[col])
    return df

EMPLOYEE_SPEC = {
    "employee_id": "cat", "hire_date": "date", "exit_date": "date",
    "status": "cat", "department": "cat", "role_family": "cat",
    "role_level": "num", "job_title": "cat", "acting_appointment": "bool",
    "salary": "num", "compa_ratio": "num", "gender": "cat",
    "age_band": "cat", "cultural_background": "cat", "contract_type": "cat",
    "hipo_flag": "bool", "promotion_eligible": "bool", "manager_id": "cat",
    "hire_source": "cat", "legacy_entity_code": "cat",
    "data_source_system": "cat", "days_to_fill": "num", "tenure_months": "num",
}

ATTRITION_SPEC = {
    "employee_id": "cat", "exit_date": "date", "exit_type": "cat",
    "stated_exit_reason": "cat", "notice_period_served": "bool",
    "regrettable_flag": "bool", "performance_band_at_exit": "cat",
    "salary_at_exit": "num", "manager_id_at_exit": "cat", "pathway": "cat",
}

ENGAGEMENT_SPEC = {
    "employee_id": "cat", "wave_number": "num", "survey_date": "date",
    "response_flag": "bool",
    **{d: "num" for d in ENGAGEMENT_DIMENSIONS},
}

PERFORMANCE_SPEC = {
    "employee_id": "cat", "review_date": "date", "performance_rating": "cat",
    "review_cycle": "cat", "promotion_recommendation": "bool",
    "goal_achievement_score": "num", "reviewer_id": "cat",
}


def clean_all(raw: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    specs = {
        "employees": EMPLOYEE_SPEC, "attrition": ATTRITION_SPEC,
        "engagement": ENGAGEMENT_SPEC, "performance": PERFORMANCE_SPEC,
    }
    return {k: clean_frame(df, specs[k]) for k, df in raw.items() if k in specs}


# Data quality profiling - this output IS a deck slide, not just housekeeping

def profile(df: pd.DataFrame, name: str, key: str = "employee_id") -> pd.DataFrame:
    rows = []
    for col in df.columns:
        s = df[col]
        rows.append({
            "table": name,
            "column": col,
            "dtype": str(s.dtype),
            "n_null": int(s.isna().sum()),
            "pct_null": round(100 * s.isna().mean(), 2),
            "n_unique": int(s.nunique(dropna=True)),
            "example": next((repr(v) for v in s.dropna().head(1)), ""),
        })
    out = pd.DataFrame(rows)

    print(f"\n  [{name}] {len(df):,} rows")
    if key in df.columns:
        dupes = int(df[key].duplicated().sum())
        print(f"    duplicate {key}: {dupes:,}")
    high_null = out[out.pct_null > 0].sort_values("pct_null", ascending=False)
    if len(high_null):
        print("    columns with nulls:")
        for _, r in high_null.head(12).iterrows():
            print(f"      {r['column']:<32} {r['pct_null']:>6.2f}%")
    return out


def reconcile(emp: pd.DataFrame, att: pd.DataFrame) -> None:
    """THE critical check: does the dataset agree with the annual report?

    Annual report: 1,400 departures in FY2025 (12 months), 10.4% voluntary attrition.
    Case brief:    attrition_log has ~1,400 rows across 24 months.
    These cannot both be true. Resolve before building anything on top.
    """
    print("\n" + "=" * 74)
    print("RECONCILIATION vs FY2025 ANNUAL REPORT")
    print("=" * 74)

    active = int((emp["status"].str.lower() == "active").sum()) if "status" in emp else np.nan
    print(f"  Active employees in data     : {active:,}   (annual report: {AR_ACTIVE_HEADCOUNT:,})")
    print(f"  Total roster rows            : {len(emp):,}")
    print(f"  Attrition log rows           : {len(att):,}   (annual report FY25: {AR_DEPARTURES_FY25:,})")

    if "exit_date" in att.columns:
        by_year = att["exit_date"].dt.year.value_counts().sort_index()
        print("\n  Exits by calendar year:")
        for yr, n in by_year.items():
            print(f"    {int(yr)}: {n:,}")

        # FY2025 = 1 Jul 2024 to 30 Jun 2025
        fy25 = att["exit_date"].between("2024-07-01", "2025-06-30").sum()
        print(f"\n  Exits in FY2025 window       : {fy25:,}   (annual report: {AR_DEPARTURES_FY25:,})")

        if "exit_type" in att.columns:
            vol = att["exit_type"].str.lower().eq("voluntary")
            fy25_vol = int((vol & att["exit_date"].between("2024-07-01", "2025-06-30")).sum())
            if active and active == active:
                rate = fy25_vol / active
                print(f"  FY2025 voluntary attrition   : {rate:.1%}   (annual report: {AR_VOLUNTARY_ATTRITION:.1%})")
                delta = abs(rate - AR_VOLUNTARY_ATTRITION)
                verdict = "CONSISTENT" if delta < 0.015 else ">>> MATERIAL DISCREPANCY <<<"
                print(f"  Verdict                      : {verdict}")

    # Orphan / coverage checks
    if "employee_id" in att.columns and "employee_id" in emp.columns:
        orphans = ~att["employee_id"].isin(emp["employee_id"])
        print(f"\n  Attrition rows with no matching employee: {int(orphans.sum()):,}")
    if "status" in emp.columns:
        departed = emp.loc[emp["status"].str.lower() == "departed", "employee_id"]
        no_log = ~departed.isin(att["employee_id"])
        print(f"  Departed employees absent from log      : {int(no_log.sum()):,}")

# Feature engineering

def engagement_features(eng: pd.DataFrame) -> pd.DataFrame:
    """A3: per-employee survey behaviour, including the non-response signal."""
    eng = eng.sort_values(["employee_id", "wave_number"])
    dims = [d for d in ENGAGEMENT_DIMENSIONS if d in eng.columns]

    eng = eng.copy()
    eng["composite"] = eng[dims].mean(axis=1) if dims else np.nan
    eng["responded"] = eng["response_flag"].fillna(False).astype(bool)

    g = eng.groupby("employee_id", observed=True)
    feat = pd.DataFrame({
        "waves_issued": g.size(),
        "waves_responded": g["responded"].sum(),
        "composite_mean": g["composite"].mean(),
        "composite_first": g["composite"].first(),
        "composite_last": g["composite"].last(),
        "composite_min": g["composite"].min(),
        "composite_std": g["composite"].std(),
    })
    feat["response_rate"] = feat["waves_responded"] / feat["waves_issued"]
    feat["never_responded"] = feat["waves_responded"] == 0
    feat["composite_trend"] = feat["composite_last"] - feat["composite_first"]

    # Terminal silence: consecutive non-responses at the end of an employee's
    # wave sequence. This is the A3 headline candidate.
    def trailing_silence(flags: pd.Series) -> int:
        n = 0
        for r in reversed(list(flags)):
            if r:
                break
            n += 1
        return n

    feat["trailing_silence"] = g["responded"].agg(trailing_silence)
    feat["went_silent"] = (feat["trailing_silence"] >= 2) & (feat["waves_responded"] > 0)

    # Persistent disengagement, for the A1 cost reconciliation.
    # Threshold is a JUDGEMENT CALL - document it and sensitivity-test it.
    low = eng.loc[eng["responded"] & (eng["composite"] < 3.0)]
    feat["waves_low"] = low.groupby("employee_id", observed=True).size()
    feat["waves_low"] = feat["waves_low"].fillna(0).astype(int)
    feat["persistently_disengaged"] = feat["waves_low"] >= 2

    # Per-dimension means, so seaborn heatmaps work straight off the clean df
    for d in dims:
        feat[f"eng_{d}"] = g[d].mean()

    return feat.reset_index()


def performance_features(perf: pd.DataFrame) -> pd.DataFrame:
    perf = perf.sort_values(["employee_id", "review_date"]).copy()
    order = {
        "Unsatisfactory": 1, "Below Expectations": 2, "Meets Expectations": 3,
        "High Performer": 4, "Outstanding": 5,
    }
    perf["rating_score"] = perf["performance_rating"].map(order)

    g = perf.groupby("employee_id", observed=True)
    feat = pd.DataFrame({
        "n_reviews": g.size(),
        "rating_mean": g["rating_score"].mean(),
        "rating_last": g["rating_score"].last(),
        "rating_first": g["rating_score"].first(),
        "goal_mean": g["goal_achievement_score"].mean(),
        "goal_last": g["goal_achievement_score"].last(),
        "n_promo_recommended": g["promotion_recommendation"].sum(),
        "last_review_date": g["review_date"].max(),
    })
    feat["rating_trend"] = feat["rating_last"] - feat["rating_first"]
    feat["ever_promo_recommended"] = feat["n_promo_recommended"] > 0
    feat["top_talent"] = feat["rating_last"] >= 4
    return feat.reset_index()


def manager_features(emp: pd.DataFrame) -> pd.DataFrame:
    """Team-level attrition. Aggregate turnover hides manager-level crises."""
    if "manager_id" not in emp.columns:
        return pd.DataFrame(columns=["manager_id", "span_of_control", "team_attrition_rate"])
    e = emp.copy()
    e["is_departed"] = e["status"].str.lower().eq("departed")
    g = e.dropna(subset=["manager_id"]).groupby("manager_id", observed=True)
    out = pd.DataFrame({
        "span_of_control": g.size(),
        "team_departures": g["is_departed"].sum(),
    })
    out["team_attrition_rate"] = out["team_departures"] / out["span_of_control"]
    return out.reset_index()


def far_features(df: pd.DataFrame) -> pd.DataFrame:
    """A2: attach each employee to their FAR wave and time-to-treatment."""
    df = df.copy()
    df["far_date"] = df["department"].map(FAR_WAVE_MAP)
    df["far_wave"] = np.where(
        df["far_date"] == FAR_ADI, "Wave 1 (ADI, Mar-2024)",
        np.where(df["far_date"] == FAR_INSURANCE_SUPER, "Wave 2 (Ins/Super, Mar-2025)", "Unmapped"),
    )
    # Regulatory-exposed roles: the population FAR actually bites on
    df["far_exposed"] = (
        df["role_family"].eq("Risk-Compliance")
        | df["department"].eq("Risk & Compliance")
    )
    if "role_level" in df.columns:
        df["far_exposed_senior"] = df["far_exposed"] & df["role_level"].ge(4)

    # Months from FAR commencement to exit (negative = left before commencement)
    df["months_to_far_at_exit"] = (
        (df["exit_date"] - df["far_date"]).dt.days / 30.44
    ).round(1)
    df["exited_post_far"] = df["exit_date"] > df["far_date"]
    return df


def cost_features(df: pd.DataFrame) -> pd.DataFrame:
    """A1: per-employee cost attribution using Finance's own constants."""
    df = df.copy()
    salary = df["salary"].fillna(AR_AVG_BASE_SALARY)

    df["replacement_cost"] = salary * REPLACEMENT_MULTIPLIER * BACKFILL_RATE
    df["replacement_cost_with_super"] = (
        salary * (1 + SUPER_ONCOST) * REPLACEMENT_MULTIPLIER * BACKFILL_RATE
    )
    df["disengagement_cost"] = salary * DISENGAGEMENT_LOSS
    df["agency_premium"] = np.where(
        df["hire_source"].eq("agency"),
        salary * AGENCY_FEE_RATE - DIRECT_HIRE_BENCHMARK,
        0.0,
    )
    return df


def build_analysis_df(clean: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """One row per employee, everything joined and derived.
    This dataframe is handed over to matplotlib and seaborn."""
    emp = clean["employees"].copy()

    # Attrition detail
    att = clean["attrition"].drop(columns=["exit_date"], errors="ignore")
    df = emp.merge(att, on="employee_id", how="left", validate="one_to_one")

    # Engagement, performance, manager context
    df = df.merge(engagement_features(clean["engagement"]), on="employee_id", how="left")
    df = df.merge(performance_features(clean["performance"]), on="employee_id", how="left")
    mgr = manager_features(emp).rename(columns={"manager_id": "_mid"})
    df = df.merge(mgr, left_on="manager_id", right_on="_mid", how="left").drop(columns=["_mid"])

    # Shared derived fields
    df["is_departed"] = df["status"].str.lower().eq("departed")
    df["is_voluntary"] = df["exit_type"].str.lower().eq("voluntary")
    df["tenure_band"] = pd.cut(df["tenure_months"], bins=TENURE_BINS, labels=TENURE_LABELS)
    df["exit_year"] = df["exit_date"].dt.year
    df["exit_month"] = df["exit_date"].dt.to_period("M").astype("string")
    df["compa_band"] = pd.cut(
        df["compa_ratio"],
        bins=[-np.inf, 0.85, 0.95, 1.05, 1.15, np.inf],
        labels=["<0.85", "0.85-0.95", "0.95-1.05", "1.05-1.15", ">1.15"],
    )
    df["is_senior"] = df["role_level"].ge(5)

    # Angle-specific
    df = far_features(df)
    df = cost_features(df)

    # Regrettable, defined two ways: HR's retrospective label vs an evidence-based definition.
    df["regrettable_hr"] = df["regrettable_flag"].fillna(False).astype(bool)
    df["regrettable_evidence"] = (
        df["is_departed"] & df["is_voluntary"]
        & (df["hipo_flag"].fillna(False).astype(bool) | df["top_talent"].fillna(False))
    )
    return df


def engagement_long(clean: dict[str, pd.DataFrame], df: pd.DataFrame) -> pd.DataFrame:
    """Wave-level frame with employee attributes attached, for seaborn
    lineplots and facet grids over time."""
    keep = [
        "employee_id", "department", "role_family", "role_level",
        "legacy_entity_code", "hire_source", "tenure_band", "compa_band",
        "is_departed", "is_voluntary", "far_wave", "far_date", "exit_date",
        "hipo_flag", "gender", "contract_type",
    ]
    keep = [c for c in keep if c in df.columns]
    eng = clean["engagement"].merge(df[keep], on="employee_id", how="left")
    dims = [d for d in ENGAGEMENT_DIMENSIONS if d in eng.columns]
    eng["composite"] = eng[dims].mean(axis=1)
    eng["responded"] = eng["response_flag"].fillna(False).astype(bool)
    if "far_date" in eng.columns:
        eng["months_to_far"] = ((eng["survey_date"] - eng["far_date"]).dt.days / 30.44).round(1)
    return eng


def monthly_exits(df: pd.DataFrame) -> pd.DataFrame:
    """Monthly exit counts by department and FAR wave, for the A2 event study."""
    d = df.loc[df["is_departed"] & df["exit_date"].notna()].copy()
    d["month"] = d["exit_date"].dt.to_period("M").dt.to_timestamp()
    grp = ["month", "department", "far_wave"]
    grp = [g for g in grp if g in d.columns]
    out = (
        d.groupby(grp, observed=True)
        .agg(
            exits=("employee_id", "size"),
            voluntary=("is_voluntary", "sum"),
            regrettable=("regrettable_hr", "sum"),
            far_exposed=("far_exposed", "sum"),
            salary_lost=("salary", "sum"),
        )
        .reset_index()
    )
    # Denominator so you can plot rates, not just counts
    head = df.groupby("department", observed=True).size().rename("headcount")
    out = out.merge(head, on="department", how="left")
    out["exit_rate_pct"] = 100 * out["exits"] / out["headcount"]
    return out
