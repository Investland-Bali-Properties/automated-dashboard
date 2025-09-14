import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Optional
from utils.formatting import abbreviate_number


def price_trend_chart(
    df: pd.DataFrame,
    agg: str = "D",
    group_by_listing_type: bool = False,
    rolling: Optional[int] = None,
    metric: str = "median",  # median or mean
    listings_rolling: Optional[int] = None,
):
    if not {"scraped_at", "price_idr"}.issubset(df.columns):
        return None
    temp = df.dropna(subset=["scraped_at", "price_idr"]).copy()
    if temp.empty:
        return None
    # ensure timezone naive for period conversion to avoid warning
    if hasattr(temp["scraped_at"].dt, "tz") and temp["scraped_at"].dt.tz is not None:
        temp["scraped_at"] = temp["scraped_at"].dt.tz_convert(None)
    temp["bucket"] = temp["scraped_at"].dt.to_period(agg).dt.to_timestamp()

    base_group = ["bucket"] + (["listing_type"] if group_by_listing_type and "listing_type" in temp.columns else [])

    price_agg = metric if metric in ("median", "mean") else "median"

    grp = temp.groupby(base_group).agg(
        price_idr=("price_idr", price_agg),
        listings=("property_id", "nunique") if "property_id" in temp.columns else ("price_idr", "count"),
    ).reset_index().sort_values("bucket")

    if rolling and rolling > 1:
        grp["price_roll"] = grp.groupby(base_group[1:] if len(base_group)>1 else [])["price_idr"].transform(lambda s: s.rolling(rolling, min_periods=1).median())
    else:
        grp["price_roll"] = grp["price_idr"]

    if listings_rolling and listings_rolling > 1:
        grp["listings_roll"] = grp.groupby(base_group[1:] if len(base_group)>1 else [])["listings"].transform(lambda s: s.rolling(listings_rolling, min_periods=1).mean())
    else:
        grp["listings_roll"] = grp["listings"]

    if grp["bucket"].nunique() == 1:
        single = grp.iloc[0].copy()
        synthetic = single.copy()
        synthetic["bucket"] = synthetic["bucket"] - pd.Timedelta("1D")
        grp = pd.concat([synthetic.to_frame().T, grp], ignore_index=True)

    fig = go.Figure()

    if group_by_listing_type and "listing_type" in grp.columns:
        for lt, sub in grp.groupby("listing_type"):
            fig.add_trace(go.Scatter(
                x=sub["bucket"], y=sub["price_roll"], mode="lines+markers",
                name=f"{price_agg.title()} {lt}",
            ))
    else:
        fig.add_trace(go.Scatter(
            x=grp["bucket"], y=grp["price_roll"], mode="lines+markers", name=f"{price_agg.title()} Price (IDR)", line=dict(color="#2155a3")
        ))

    if group_by_listing_type and "listing_type" in grp.columns:
        for lt, sub in grp.groupby("listing_type"):
            fig.add_trace(go.Bar(
                x=sub["bucket"], y=sub["listings_roll"], name=f"Listings {lt}", opacity=0.35, yaxis="y2"
            ))
    else:
        fig.add_trace(go.Bar(x=grp["bucket"], y=grp["listings_roll"], name="Listings", marker_color="#9ec3e6", opacity=0.35, yaxis="y2"))

    # Y-axis tick formatting (abbreviated)
    y_vals = grp["price_roll"].dropna()
    ticks = sorted(y_vals.quantile([0,0.25,0.5,0.75,1]).unique()) if not y_vals.empty else []
    ticktext = [abbreviate_number(t) for t in ticks]

    fig.update_layout(
        title=(f"{price_agg.title()} Price & Listings Over Time (agg={agg}" +
               (", grouped" if group_by_listing_type else "") +
               (f", roll={rolling}" if rolling and rolling>1 else "") +
               (f", list_roll={listings_rolling}" if listings_rolling and listings_rolling>1 else "") + ")"),
        margin=dict(l=10, r=10, t=60, b=10),
        xaxis_title="Date",
        yaxis=dict(title=f"{price_agg.title()} Price (IDR)", tickmode="array", tickvals=ticks, ticktext=ticktext),
        yaxis2=dict(title="Listings", overlaying="y", side="right", showgrid=False),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        barmode="stack" if group_by_listing_type else "relative",
    )

    return fig


def price_distribution_chart(df: pd.DataFrame):
    if "price_per_sqm_idr" not in df.columns:
        return None
    fig = px.histogram(df, x="price_per_sqm_idr", nbins=40, title="Price per sqm Distribution (IDR)")
    fig.update_layout(margin=dict(l=10,r=10,t=40,b=10))
    return fig


def price_per_sqm_by_area(df: pd.DataFrame, top_n: int = 15):
    if not {"area", "price_per_sqm_idr"}.issubset(df.columns):
        return None
    grp = (
        df.dropna(subset=["area", "price_per_sqm_idr"])\
          .groupby("area")
          .agg(median_ppsqm=("price_per_sqm_idr", "median"), listings=("property_id", "count"))
          .reset_index()
    )
    grp = grp.sort_values("median_ppsqm", ascending=False).head(top_n)
    fig = px.bar(grp, x="area", y="median_ppsqm", hover_data=["listings"], title=f"Top {top_n} Areas by Median Price per sqm (IDR)")
    fig.update_layout(xaxis_title="Area", yaxis_title="Median Price / sqm (IDR)", margin=dict(l=10,r=10,t=50,b=80))
    return fig


def boxplot_price_per_sqm(df: pd.DataFrame):
    if not {"property_type", "price_per_sqm_idr"}.issubset(df.columns):
        return None
    temp = df.dropna(subset=["property_type", "price_per_sqm_idr"]).copy()
    fig = px.box(temp, x="property_type", y="price_per_sqm_idr", title="Price per sqm by Property Type (IDR)")
    fig.update_layout(margin=dict(l=10,r=10,t=50,b=80))
    return fig


def rent_vs_sale_distribution(df: pd.DataFrame):
    if not {"listing_type", "price_per_sqm_idr"}.issubset(df.columns):
        return None
    temp = df[df["listing_type"].isin(["for_sale", "for_rent"])].dropna(subset=["price_per_sqm_idr"]).copy()
    if temp.empty:
        return None
    fig = px.violin(temp, x="listing_type", y="price_per_sqm_idr", box=True, points="suspectedoutliers", title="Rent vs Sale Price per sqm Distribution (IDR)")
    fig.update_layout(margin=dict(l=10,r=10,t=50,b=60))
    return fig
