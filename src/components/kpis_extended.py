import pandas as pd
from typing import Optional, List

# Helper detection functions

def _detect_sale_mask(df: pd.DataFrame) -> pd.Series:
    cols = [c for c in ["listing_type","property_status","status"] if c in df.columns]
    if not cols:
        return pd.Series([True]*len(df), index=df.index)  # assume all sale if unknown
    combined = pd.Series([' '.join(str(df.loc[i, c]).lower() for c in cols) for i in df.index], index=df.index)
    return combined.str.contains('sale') & ~combined.str.contains('rent')

def _detect_active_mask(df: pd.DataFrame) -> pd.Series:
    # Available vs sold/rented/off-market
    cols = [c for c in ["availability","property_status","status"] if c in df.columns]
    if not cols:
        return pd.Series([True]*len(df), index=df.index)
    combined = pd.Series([' '.join(str(df.loc[i, c]).lower() for c in cols) for i in df.index], index=df.index)
    return ~combined.str.contains('sold|rented|inactive|off')

def _region_column(df: pd.DataFrame) -> Optional[str]:
    for c in ["area","region","location","city"]:
        if c in df.columns:
            return c
    return None

def _bedroom_column(df: pd.DataFrame) -> Optional[str]:
    for c in ["bedrooms","beds"]:
        if c in df.columns:
            return c
    return None

# KPI 1: Median Sales Price by bedroom & area

def median_sales_price(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    sale_mask = _detect_sale_mask(df)
    region_col = _region_column(df)
    bed_col = _bedroom_column(df)
    cols = []
    if bed_col: cols.append(bed_col)
    if region_col: cols.append(region_col)
    if 'price_idr' not in df.columns or not cols:
        return pd.DataFrame()
    g = df.loc[sale_mask & df['price_idr'].notna(), cols + ['price_idr']]
    if g.empty:
        return pd.DataFrame()
    out = g.groupby(cols).agg(median_sale_price_idr=('price_idr','median'), count=('price_idr','count')).reset_index()
    return out.sort_values('median_sale_price_idr', ascending=False)

# KPI 2: Median Available Price by bedroom & area

def median_available_price(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    active_mask = _detect_active_mask(df)
    region_col = _region_column(df)
    bed_col = _bedroom_column(df)
    cols = []
    if bed_col: cols.append(bed_col)
    if region_col: cols.append(region_col)
    if 'price_idr' not in df.columns or not cols:
        return pd.DataFrame()
    g = df.loc[active_mask & df['price_idr'].notna(), cols + ['price_idr']]
    if g.empty:
        return pd.DataFrame()
    out = g.groupby(cols).agg(median_available_price_idr=('price_idr','median'), count=('price_idr','count')).reset_index()
    return out.sort_values('median_available_price_idr', ascending=False)

# KPI 3: Price per SQM overall & by region

def price_per_sqm_region(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    pps_col = None
    if 'price_per_sqm_idr' in df.columns:
        pps_col = 'price_per_sqm_idr'
    elif {'price_idr','building_size_sqm'}.issubset(df.columns):
        df = df.copy()
        df['__pps_calc'] = df.apply(lambda r: r['price_idr']/r['building_size_sqm'] if r['price_idr'] and r['building_size_sqm'] and r['building_size_sqm']>0 else None, axis=1)
        pps_col = '__pps_calc'
    else:
        return pd.DataFrame()
    region_col = _region_column(df)
    if not region_col:
        return pd.DataFrame()
    g = df.dropna(subset=[pps_col])[[region_col, pps_col]]
    if g.empty:
        return pd.DataFrame()
    out = g.groupby(region_col).agg(median_pps_idr=(pps_col,'median'), listings=(pps_col,'count')).reset_index().sort_values('median_pps_idr', ascending=False)
    overall = pd.DataFrame({'overall_median_pps_idr':[g[pps_col].median()], 'overall_listings':[len(g)]})
    return out, overall

# KPI 4: Supply Growth by segment & region (month over month%)

def supply_growth(df: pd.DataFrame, segment_col: str = 'property_type') -> pd.DataFrame:
    if df.empty or 'scraped_at' not in df.columns:
        return pd.DataFrame()
    region_col = _region_column(df)
    if region_col is None:
        return pd.DataFrame()
    if segment_col not in df.columns:
        segment_col = region_col  # fallback
    temp = df.dropna(subset=['scraped_at']).copy()
    if temp.empty:
        return pd.DataFrame()
    temp['month'] = temp['scraped_at'].dt.to_period('M').dt.to_timestamp()
    grp = temp.groupby(['month', region_col, segment_col]).agg(active=('property_id','nunique')).reset_index()
    grp = grp.sort_values('month')
    grp['prev_active'] = grp.groupby([region_col, segment_col])['active'].shift(1)
    grp['mom_growth_pct'] = (grp['active'] - grp['prev_active'])/grp['prev_active']*100
    return grp

# KPI 5: Leasehold vs Freehold Share

def leasehold_freehold_share(df: pd.DataFrame) -> pd.DataFrame:
    tenure_col = None
    for c in ['tenure','ownership','ownership_type','land_title','title_type']:
        if c in df.columns:
            tenure_col = c
            break
    if tenure_col is None:
        # Attempt pattern search in description/title (lightweight)
        possible = []
        if 'title' in df.columns:
            possible.append(df['title'])
        if 'description' in df.columns:
            possible.append(df['description'])
        if not possible:
            return pd.DataFrame()
        combo = pd.concat(possible, axis=0).astype(str).str.lower()
        # This is expensive for large sets; skip full parse, return empty placeholder
        return pd.DataFrame()
    temp = df[[tenure_col]].dropna().copy()
    if temp.empty:
        return pd.DataFrame()
    temp['tenure_clean'] = temp[tenure_col].astype(str).str.lower()
    temp.loc[temp['tenure_clean'].str.contains('lease'), 'tenure_bucket'] = 'Leasehold'
    temp.loc[temp['tenure_clean'].str.contains('free'), 'tenure_bucket'] = 'Freehold'
    temp['tenure_bucket'].fillna('Other/Unknown', inplace=True)
    share = temp['tenure_bucket'].value_counts(normalize=True).mul(100).round(2).reset_index()
    share.columns = ['tenure_bucket','pct_share']
    return share

# KPI 6: Days Listed stats (requires first_seen & last_seen or created_at)

def days_listed_stats(df: pd.DataFrame) -> pd.DataFrame:
    date_cols = [c for c in ['first_seen','created_at','listed_at'] if c in df.columns]
    end_cols = [c for c in ['last_seen','updated_at'] if c in df.columns]
    if not date_cols or 'scraped_at' not in df.columns:
        return pd.DataFrame()
    start_col = date_cols[0]
    end_col = end_cols[0] if end_cols else 'scraped_at'
    temp = df.dropna(subset=[start_col, end_col]).copy()
    if temp.empty:
        return pd.DataFrame()
    temp['days_listed'] = (temp[end_col] - temp[start_col]).dt.days
    stats = temp['days_listed'].describe()[['count','mean','min','max','50%']].to_dict()
    return pd.DataFrame([{
        'count': int(stats['count']),
        'avg_days': round(stats['mean'],2),
        'min_days': int(stats['min']),
        'median_days': int(stats['50%']),
        'max_days': int(stats['max'])
    }])

