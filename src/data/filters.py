"""
Filter utilities that apply global dashboard filters to the listings dataset.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple, List

import pandas as pd


@dataclass
class GlobalFilters:
    date_range: Tuple[Optional[pd.Timestamp], Optional[pd.Timestamp]]
    date_granularity: str
    listing_type: Optional[str]
    property_types: Optional[list]
    areas: Optional[list]
    bedrooms_bucket: Optional[list]
    ownership: Optional[list]
    property_status: Optional[list]
    seller_type: Optional[list]
    price_range: Optional[Tuple[Optional[float], Optional[float]]]
    rent_range: Optional[Tuple[Optional[float], Optional[float]]]
    building_size_range: Optional[Tuple[Optional[float], Optional[float]]]
    land_size_range: Optional[Tuple[Optional[float], Optional[float]]]
    currency: str
    hide_outliers: bool
    basis_ppsy: str
    assumed_freehold_horizon: int
    ppsy_toggle_freehold: bool


DEFAULT_FILTERS = GlobalFilters(
    date_range=(None, None),
    date_granularity="M",
    listing_type=None,
    property_types=None,
    areas=None,
    bedrooms_bucket=None,
    ownership=None,
    property_status=None,
    seller_type=None,
    price_range=None,
    rent_range=None,
    building_size_range=None,
    land_size_range=None,
    currency="IDR",
    hide_outliers=False,
    basis_ppsy="building",
    assumed_freehold_horizon=30,
    ppsy_toggle_freehold=False,
)


def apply_global_filters(df: pd.DataFrame, filters: GlobalFilters) -> pd.DataFrame:
    """
    Apply the currently selected filter values to the enriched listings dataset.

    The implementation here is a placeholder that will be extended with the
    full filtering logic (including outlier trimming) in a later step.
    """
    if df.empty:
        return df
    filtered = df.copy()

    # Date filtering uses the effective listing date fallback
    start, end = filters.date_range
    date_col_candidates: List[str] = [
        "listing_date_effective",
        "listing_date",
        "scraped_at",
    ]
    date_col = next((col for col in date_col_candidates if col in filtered.columns), None)
    if date_col:
        if start is not None:
            filtered = filtered[filtered[date_col] >= start]
        if end is not None:
            filtered = filtered[filtered[date_col] <= end]

    if filters.listing_type and "listing_type" in filtered:
        filtered = filtered[
            filtered["listing_type"].astype(str).str.lower() == filters.listing_type.lower()
        ]

    if filters.property_types and "property_type" in filtered:
        filtered = filtered[filtered["property_type"].isin(filters.property_types)]

    if filters.areas and "area" in filtered:
        filtered = filtered[filtered["area"].isin(filters.areas)]

    if filters.ownership and "ownership_type" in filtered:
        # Apply ownership filtering only for 'for sale' listings to avoid
        # unintentionally excluding rentals labeled as 'Yearly Rental' (data hygiene).
        if "listing_type" in filtered:
            sale_mask = filtered["listing_type"].astype(str).str.lower() == "for sale"
            keep_mask = (~sale_mask) | (filtered["ownership_type"].isin(filters.ownership))
            filtered = filtered[keep_mask]
        else:
            filtered = filtered[filtered["ownership_type"].isin(filters.ownership)]

    if filters.property_status and "property_status" in filtered:
        filtered = filtered[filtered["property_status"].isin(filters.property_status)]

    seller_columns = ["seller_type", "source_category", "listing_agency_type"]
    seller_col = next((col for col in seller_columns if col in filtered.columns), None)
    if filters.seller_type and seller_col:
        filtered = filtered[filtered[seller_col].isin(filters.seller_type)]

    if filters.bedrooms_bucket and "bedrooms" in filtered:
        bucket_map = {
            "1": (1, 1),
            "2": (2, 2),
            "3-4": (3, 4),
            "5+": (5, None),
        }
        bucket_masks = []
        for bucket in filters.bedrooms_bucket:
            low, high = bucket_map.get(bucket, (None, None))
            if low is None and high is None:
                continue
            mask = filtered["bedrooms"].notna()
            if low is not None:
                mask &= filtered["bedrooms"] >= low
            if high is not None:
                mask &= filtered["bedrooms"] <= high
            bucket_masks.append(mask)
        if bucket_masks:
            combined_mask = bucket_masks[0]
            for mask in bucket_masks[1:]:
                combined_mask |= mask
            filtered = filtered[combined_mask]

    if filters.price_range and "price_sale_idr" in filtered:
        price_min, price_max = filters.price_range
        price_series = filtered["price_sale_idr"].fillna(filtered.get("price_idr"))
        price_series = pd.to_numeric(price_series, errors="coerce")
        if price_min is not None:
            filtered = filtered[price_series >= price_min]
        if price_max is not None:
            filtered = filtered[price_series <= price_max]

    if filters.rent_range and "rent_price_month_idr_norm" in filtered:
        rent_min, rent_max = filters.rent_range
        rent_series = pd.to_numeric(filtered["rent_price_month_idr_norm"], errors="coerce")
        if rent_min is not None:
            filtered = filtered[rent_series >= rent_min]
        if rent_max is not None:
            filtered = filtered[rent_series <= rent_max]

    if filters.building_size_range and "building_size_sqm" in filtered:
        size_min, size_max = filters.building_size_range
        size_series = pd.to_numeric(filtered["building_size_sqm"], errors="coerce")
        if size_min is not None:
            filtered = filtered[size_series >= size_min]
        if size_max is not None:
            filtered = filtered[size_series <= size_max]

    if filters.land_size_range and "land_size_sqm" in filtered:
        land_min, land_max = filters.land_size_range
        land_series = pd.to_numeric(filtered["land_size_sqm"], errors="coerce")
        if land_min is not None:
            filtered = filtered[land_series >= land_min]
        if land_max is not None:
            filtered = filtered[land_series <= land_max]

    if filters.hide_outliers and "is_outlier_any" in filtered:
        filtered = filtered[~filtered["is_outlier_any"]]

    if filters.assumed_freehold_horizon > 0 and "price_per_sqm_idr_calc" in filtered:
        filtered = filtered.copy()
        filtered["price_per_sqm_per_year_freehold_assumed"] = (
            filtered["price_per_sqm_idr_calc"] / filters.assumed_freehold_horizon
        )

    filtered.attrs["applied_filters"] = serialize_filters(filters)
    return filtered


def serialize_filters(filters: GlobalFilters) -> Dict[str, Any]:
    """
    Convert the GlobalFilters dataclass to a JSON-serialisable dictionary to be
    stored in session_state or used for logging/debugging.
    """
    return {
        "date_range": tuple(
            v.isoformat() if hasattr(v, "isoformat") else v for v in filters.date_range
        ),
        "listing_type": filters.listing_type,
        "date_granularity": filters.date_granularity,
        "property_types": filters.property_types,
        "areas": filters.areas,
        "bedrooms_bucket": filters.bedrooms_bucket,
        "ownership": filters.ownership,
        "property_status": filters.property_status,
        "seller_type": filters.seller_type,
        "price_range": filters.price_range,
        "rent_range": filters.rent_range,
        "building_size_range": filters.building_size_range,
        "land_size_range": filters.land_size_range,
        "currency": filters.currency,
        "hide_outliers": filters.hide_outliers,
        "basis_ppsy": filters.basis_ppsy,
        "assumed_freehold_horizon": filters.assumed_freehold_horizon,
        "ppsy_toggle_freehold": filters.ppsy_toggle_freehold,
    }
