"""
Data enrichment helpers responsible for computing derived metrics required
across the dashboard.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Iterable, Tuple

import numpy as np
import pandas as pd


LEASE_REGEX = re.compile(r"(\d{1,2})\s*(?:years|year|yrs|yr|th|tahun)", re.IGNORECASE)
CURRENT_YEAR = datetime.utcnow().year


def _to_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def _coerce_datetime(series: pd.Series) -> pd.Series:
    parsed = pd.to_datetime(series, errors="coerce", utc=True)
    if pd.api.types.is_datetime64_any_dtype(parsed):
        return parsed.dt.tz_convert(None)
    return parsed


def _compute_price_sale_idr(df: pd.DataFrame) -> pd.Series:
    series = pd.Series(np.nan, index=df.index, dtype="float64")
    listing_type = df.get("listing_type")
    if listing_type is not None:
        mask_sale = listing_type.astype(str).str.lower().eq("for sale")
    else:
        mask_sale = pd.Series(False, index=df.index)
    sale_price = df.get("sale_price_idr")
    base_price = df.get("price_idr")
    if sale_price is not None:
        sale_numeric = _to_numeric(sale_price)
        series.loc[mask_sale] = sale_numeric[mask_sale]
    if base_price is not None:
        base_numeric = _to_numeric(base_price)
        series.loc[mask_sale & series.isna()] = base_numeric[mask_sale & series.isna()]
    return series


def _normalise_rent_month(df: pd.DataFrame) -> pd.Series:
    rent_norm = pd.Series(np.nan, index=df.index, dtype="float64")
    month_price = df.get("rent_price_month_idr")
    if month_price is not None:
        rent_norm = _to_numeric(month_price)
    rent_period = (
        df.get("rent_period_base")
        if "rent_period_base" in df.columns
        else df.get("rent_period")
    )
    base_price = df.get("price_idr")
    fallback_price = _to_numeric(base_price) if base_price is not None else rent_norm

    if rent_period is None:
        return rent_norm

    normalized_period = rent_period.astype(str).str.lower().str.strip()
    price = rent_norm.copy()

    mask_missing = price.isna() & fallback_price.notna()
    if not mask_missing.any():
        return price

    daily_aliases = {"day", "daily", "harian"}
    weekly_aliases = {"week", "weekly", "mingguan"}
    monthly_aliases = {"month", "monthly", "bulanan"}
    yearly_aliases = {"year", "yearly", "annual", "annually", "tahun"}

    price.loc[mask_missing & normalized_period.isin(daily_aliases)] = (
        fallback_price[mask_missing & normalized_period.isin(daily_aliases)] * 30
    )
    price.loc[mask_missing & normalized_period.isin(weekly_aliases)] = (
        fallback_price[mask_missing & normalized_period.isin(weekly_aliases)] * 4.3
    )
    price.loc[mask_missing & normalized_period.isin(monthly_aliases)] = fallback_price[
        mask_missing & normalized_period.isin(monthly_aliases)
    ]
    price.loc[mask_missing & normalized_period.isin(yearly_aliases)] = (
        fallback_price[mask_missing & normalized_period.isin(yearly_aliases)] / 12
    )

    return price


def _estimate_lease_years(row: pd.Series) -> float:
    ownership = str(row.get("ownership_type", "") or "").lower()
    if ownership != "leasehold":
        return np.nan

    lease_duration = row.get("lease_duration")
    if pd.notna(lease_duration):
        if isinstance(lease_duration, (int, float)):
            return float(np.clip(lease_duration, 1, 99))
        if isinstance(lease_duration, str):
            match = LEASE_REGEX.search(lease_duration)
            if match:
                years = float(match.group(1))
                return float(np.clip(years, 1, 99))
            try:
                parsed = float(lease_duration.strip())
                return float(np.clip(parsed, 1, 99))
            except Exception:
                pass

    expiry = row.get("lease_expiry_year")
    if pd.notna(expiry):
        try:
            years = float(expiry) - CURRENT_YEAR
            if years > 0:
                return float(np.clip(years, 1, 99))
        except Exception:
            pass

    description = row.get("description")
    if isinstance(description, str):
        match = LEASE_REGEX.search(description)
        if match:
            years = float(match.group(1))
            return float(np.clip(years, 1, 99))

    return np.nan


def _compute_price_per_sqm(df: pd.DataFrame) -> Tuple[pd.Series, pd.Series]:
    building_size = _to_numeric(df.get("building_size_sqm", pd.Series(np.nan, index=df.index)))
    land_size = _to_numeric(df.get("land_size_sqm", pd.Series(np.nan, index=df.index)))
    price_sale = _to_numeric(df.get("price_sale_idr", pd.Series(np.nan, index=df.index)))

    price_per_sqm_building = price_sale / building_size.replace({0: np.nan})
    fallback = price_sale / land_size.replace({0: np.nan})
    price_per_sqm = price_per_sqm_building.fillna(fallback)

    price_per_sqm_land = price_sale / land_size.replace({0: np.nan})

    return price_per_sqm, price_per_sqm_land


def _flag_outliers(df: pd.DataFrame, columns: Iterable[str], lower: float = 0.01, upper: float = 0.99) -> pd.DataFrame:
    df = df.copy()
    for col in columns:
        if col not in df or df[col].dropna().empty:
            df[f"is_outlier_{col}"] = False
            continue
        q_low, q_high = df[col].quantile([lower, upper])
        mask = df[col].notna() & ((df[col] < q_low) | (df[col] > q_high))
        df[f"is_outlier_{col}"] = mask
        df.attrs.setdefault("outlier_thresholds", {})[col] = {
            "lower": float(q_low),
            "upper": float(q_high),
        }
    outlier_cols = [c for c in df.columns if c.startswith("is_outlier_")]
    df["is_outlier_any"] = df[outlier_cols].any(axis=1) if outlier_cols else False
    return df


def enrich_listings(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute derived metrics such as normalized rent, PPSY, days listed, and
    outlier flags required by the dashboard.
    """
    if df.empty:
        return df

    working = df.copy()

    # Ensure numeric coercion for primary quantitative fields
    numeric_cols = [
        "price_idr",
        "sale_price_idr",
        "rent_price_month_idr",
        "rent_price_year_idr",
        "rent_price_week_idr",
        "rent_price_day_idr",
        "rent_price_month_idr_norm",
        "bedrooms",
        "bathrooms",
        "land_size_sqm",
        "building_size_sqm",
        "lease_duration",
        "lease_expiry_year",
    ]
    for col in numeric_cols:
        if col in working.columns:
            working[col] = _to_numeric(working[col])

    # Datetime coercion and helper reference column
    for col in ("scraped_at", "listing_date"):
        if col in working.columns:
            working[col] = _coerce_datetime(working[col])

    # Fallback listing date for filtering/analysis
    if "listing_date" in working.columns:
        fallback = working["listing_date"].fillna(working.get("scraped_at"))
    else:
        fallback = working.get("scraped_at")
    working["listing_date_effective"] = _coerce_datetime(fallback)

    # Derived price fields
    working["price_sale_idr"] = _compute_price_sale_idr(working)
    working["rent_price_month_idr_norm"] = _normalise_rent_month(working)
    working["adr_idr"] = working["rent_price_month_idr_norm"] / 30.0

    working["lease_years_remaining"] = working.apply(_estimate_lease_years, axis=1)

    price_per_sqm, price_per_sqm_land = _compute_price_per_sqm(working)
    working["price_per_sqm_idr_calc"] = price_per_sqm
    working["price_per_sqm_land_idr_calc"] = price_per_sqm_land

    # Price per sqm per year (PPSY) for leasehold listings
    working["price_per_sqm_per_year"] = np.where(
        working["lease_years_remaining"] > 0,
        working["price_per_sqm_idr_calc"] / working["lease_years_remaining"],
        np.nan,
    )

    # Freehold PPSY baseline with 30-year horizon default
    assumed_horizon_years = 30
    working["price_per_sqm_per_year_freehold"] = np.where(
        working["price_per_sqm_idr_calc"].notna(),
        working["price_per_sqm_idr_calc"] / assumed_horizon_years,
        np.nan,
    )

    # Annual rent per sqm (building basis)
    building_size = working.get("building_size_sqm")
    working["annual_rent_per_sqm"] = np.where(
        (working["rent_price_month_idr_norm"].notna()) & (building_size.notna()) & (building_size > 0),
        (working["rent_price_month_idr_norm"] * 12) / building_size,
        np.nan,
    )

    # Proxy gross yield at listing level
    working["yield_pct_proxy"] = np.where(
        (working["annual_rent_per_sqm"].notna()) & (working["price_per_sqm_idr_calc"].notna()),
        (working["annual_rent_per_sqm"] / working["price_per_sqm_idr_calc"]) * 100,
        np.nan,
    )

    # Days listed calculation
    current_ts = pd.Timestamp.utcnow().tz_localize(None)
    if "scraped_at" in working.columns:
        reference_date = _coerce_datetime(working["scraped_at"]).fillna(current_ts)
    else:
        reference_date = pd.Series(current_ts, index=working.index, dtype="datetime64[ns]")

    if "listing_date_effective" in working.columns:
        listing_dates = _coerce_datetime(working["listing_date_effective"])
        diff = reference_date - listing_dates
        working["days_listed"] = np.where(
            listing_dates.notna(),
            diff.dt.days.clip(lower=0),
            np.nan,
        )
    else:
        working["days_listed"] = np.nan

    # Track source diagnostics
    working.attrs["diagnostics"] = {
        "rows": int(len(working)),
        "computed_at": datetime.utcnow().isoformat(),
    }

    enriched = _flag_outliers(
        working,
        columns=[
            "price_sale_idr",
            "rent_price_month_idr_norm",
            "price_per_sqm_idr_calc",
            "price_per_sqm_per_year",
            "annual_rent_per_sqm",
            "yield_pct_proxy",
        ],
    )

    return enriched
