import pandas as pd
from typing import Dict, Any


def apply_filters(df: pd.DataFrame, filters: Dict[str, Any]) -> pd.DataFrame:
    out = df.copy()
    if filters.get("property_type") and "property_type" in out:
        out = out[out["property_type"].isin(filters["property_type"])]
    if filters.get("area") and "area" in out:
        out = out[out["area"].isin(filters["area"])]
    # Price range
    if "price_idr" in out.columns:
        lo = filters.get("price_idr_min")
        hi = filters.get("price_idr_max")
        include_missing_price = filters.get("include_missing_price", True)
        if lo is not None:
            if include_missing_price:
                out = out[(out["price_idr"].isna()) | (out["price_idr"] >= lo)]
            else:
                out = out[out["price_idr"] >= lo]
        if hi is not None:
            if include_missing_price:
                out = out[(out["price_idr"].isna()) | (out["price_idr"] <= hi)]
            else:
                out = out[out["price_idr"] <= hi]
    # Bedrooms
    if filters.get("bedrooms") and "bedrooms" in out:
        blo, bhi = filters["bedrooms"]
        include_missing_bedrooms = filters.get("include_missing_bedrooms", True)
        if include_missing_bedrooms:
            out = out[(out["bedrooms"].isna()) | ((out["bedrooms"] >= blo) & (out["bedrooms"] <= bhi))]
        else:
            out = out[(out["bedrooms"] >= blo) & (out["bedrooms"] <= bhi)]
    # Date range filtering
    if filters.get("date_range") and any(c in out.columns for c in ["listing_date","scraped_at"]):
        start, end = filters["date_range"]
        date_col = None
        if "listing_date" in out.columns and pd.api.types.is_datetime64_any_dtype(out["listing_date"]):
            date_col = "listing_date"
        elif "scraped_at" in out.columns and pd.api.types.is_datetime64_any_dtype(out["scraped_at"]):
            date_col = "scraped_at"
        if date_col and (start or end):
            base = out.copy()
            dated = base[base[date_col].notna()]
            if start:
                dated = dated[dated[date_col] >= pd.to_datetime(start)]
            if end:
                dated = dated[dated[date_col] <= pd.to_datetime(end)]
            missing = base[base[date_col].isna()]
            out = pd.concat([dated, missing], ignore_index=True)
    return out
