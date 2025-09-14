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
        if lo is not None:
            out = out[out["price_idr"] >= lo]
        if hi is not None:
            out = out[out["price_idr"] <= hi]
    # Bedrooms
    if filters.get("bedrooms") and "bedrooms" in out:
        blo, bhi = filters["bedrooms"]
        out = out[(out["bedrooms"] >= blo) & (out["bedrooms"] <= bhi)]
    return out
