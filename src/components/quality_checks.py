import pandas as pd
from typing import Dict, Any

ASSUMED_FX = 15500


def missing_values_summary(df: pd.DataFrame) -> pd.DataFrame:
    # base missing (NaN/NaT)
    mv_series = df.isna().sum()
    # treat blank strings as missing (after sentinel normalization this should be rare but safe)
    for col in df.columns:
        if df[col].dtype == object:
            blanks = df[col].apply(lambda v: isinstance(v, str) and v.strip() == "")
            if blanks.any():
                mv_series[col] += blanks.sum()
    mv = mv_series.reset_index()
    mv.columns = ["column","missing_count"]
    mv["missing_pct"] = mv["missing_count"] / len(df) * 100 if len(df)>0 else 0
    return mv.sort_values("missing_pct", ascending=False)


def duplicate_count(df: pd.DataFrame) -> int:
    if "property_id" in df.columns:
        return df.duplicated(subset=["property_id"]).sum()
    return df.duplicated().sum()


def exchange_rate_consistency(df: pd.DataFrame) -> pd.DataFrame:
    if not {"price_idr","price_usd"}.issubset(df.columns):
        return pd.DataFrame()
    temp = df.dropna(subset=["price_idr","price_usd"]).copy()
    temp = temp[temp["price_usd"]>0]
    if temp.empty:
        return pd.DataFrame()
    temp["implied_fx"] = temp["price_idr"] / temp["price_usd"]
    temp["fx_dev_pct"] = (temp["implied_fx"] - ASSUMED_FX)/ASSUMED_FX * 100
    return temp[[c for c in ["property_id","company","price_idr","price_usd","implied_fx","fx_dev_pct"] if c in temp.columns]]


def build_quality_overview(df: pd.DataFrame) -> Dict[str, Any]:
    return {
        "row_count": len(df),
        "duplicate_count": duplicate_count(df),
        "distinct_properties": df["property_id"].nunique() if "property_id" in df.columns else None,
    }
