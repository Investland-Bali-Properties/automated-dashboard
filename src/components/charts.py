import pandas as pd
import plotly.express as px


def price_trend_chart(df: pd.DataFrame):
    if not {"scraped_at", "price_idr"}.issubset(df.columns):
        return None
    temp = df.copy()
    temp["scraped_date"] = temp["scraped_at"].dt.date
    grp = temp.groupby("scraped_date").agg(median_price_idr=("price_idr", "median"), listings=("property_id", "count"))
    grp = grp.reset_index()
    fig = px.line(grp, x="scraped_date", y="median_price_idr", title="Median Price (IDR) Over Time")
    fig.update_layout(margin=dict(l=10,r=10,t=40,b=10))
    return fig


def price_distribution_chart(df: pd.DataFrame):
    if "price_per_sqm_idr" not in df.columns:
        return None
    fig = px.histogram(df, x="price_per_sqm_idr", nbins=40, title="Price per sqm Distribution (IDR)")
    fig.update_layout(margin=dict(l=10,r=10,t=40,b=10))
    return fig
