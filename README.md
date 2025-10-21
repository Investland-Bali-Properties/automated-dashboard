# Bali Real Estate Intelligence Dashboard

Streamlit application providing analytics for Bali real-estate listings with a focus on leasehold PPSY, supply velocity, rental ADR, and company benchmarking. The app consumes data from a Google Sheet (temporary dataset `[Silvertest]Betterplace`) and exposes a comprehensive set of filters, derived metrics, and tabbed insights.

## 1. Quick Start

1. **Environment variables** - create `.env` in project root:

   ```env
   SPREADSHEET_ID=1I-iGdqCiYwIJuwG-91E1CGTDD6blOkGPr-rJJvtUxBk
   SHEET_NAME=[Silvertest]Betterplace
   GOOGLE_APPLICATION_CREDENTIALS=google-credentials.json
   ```

2. **Service account** - place the `google-credentials.json` file in the project root and share the worksheet with the service account email.

3. **Install dependencies** (use existing `venv` or your own environment):

   ```bash
   pip install -r requirements.txt
   ```

4. **Run Streamlit**:

   ```bash
   streamlit run app.py
   ```

5. **Refresh data** any time via the sidebar "Refresh Data" button (clears the cached Google Sheet pull).

## 2. Global Filters & Controls

- Listing type, region/area, property type, ownership, property status, seller type
- Bedrooms bucket (Studio, 1, 2, 3-4, 5+), price/rent/size ranges
- Date range presets (All, 5Y, 3Y, 1Y, 6M, YTD, QTD, Custom) with configurable granularity (D/W/M/Q)
- Currency toggle (IDR <-> USD, default FX fallback 15,000 when USD columns absent)
- Outlier toggle (drops rows flagged as P1-P99 outliers)
- PPSY options: basis Building vs Land, optional Freehold horizon slider

## 3. Tabs & Highlights

| Tab | Highlights |
| --- | ---------- |
| **Overview** | KPI cards (Median Sales, Rent, PPSY, Days Listed, Supply, Sales Volume), trends for sales/rent/PPSY, ownership mix, supply by region, regional movers leaderboard |
| **Sales Market** | Leasehold PPSY heatmap (Bedrooms x Area), PPSY distribution by area, PPSY trend with MA, lease tenure scatter, price vs size scatter (log option), value opportunity table |
| **Rental Market** | ADR/occupancy KPIs, ADR by bedrooms vs seller type, ADR heatmap, ADR & occupancy trends, ADR histogram, occupancy leader/laggard tables |
| **Supply & Velocity** | New listings trend (stacked), sales volume bars, days-listed distribution, regional leaderboard (growth, median days, conversion) |
| **Ownership Mix** | Leasehold vs freehold share by region, price per SQM comparison, optional PPSY comparison (freehold horizon), tenure share trend, summary table |
| **Off-plan vs Ready** | PPSY comparison by area/bedrooms, off-plan share trend, days-listed boxplot by status |
| **Regional Insights** | Metric map / ranking, top-N region charts, metric trends for top regions, regional summary table |
| **Data Source Insight** | Company-level listings, median price/rent/PPSY/ADR, recommendations based on supply, premium positioning, and value |
| **Explorer** | Searchable table with selectable columns, downloads filtered results |
| **Data Quality & Definitions** | Health tiles (missing size, price parse fails, lease years, PPSY outliers), diagnostics attributes, metric definitions, model assumptions |

## 4. Project Structure

```
app.py                    # Streamlit entry point
src/
  __init__.py
  config.py               # Tab definitions
  data/
    loader.py             # Google Sheet loader with caching & normalization
    enrichment.py         # Derived metrics (PPSY, ADR, lease horizon, outliers)
    filters.py            # Global filter dataclass + logic
  ui/
    layout.py             # Sidebar + page config
    components/           # Reusable KPIs, charts, tables, formatting
    pages/                # Tab renderers (overview, sales, rental, etc.)
    utils/
      currency.py         # FX conversion helpers
  ...
requirements.txt
.streamlit/config.toml    # Theme defaults
```

Legacy implementation is preserved in `OLD-CODE/` for reference.

## 5. Data Enrichment & Assumptions

- **Rent normalisation**: daily x30, weekly x4.3, yearly /12; ADR = monthly /30.
- **Price per SQM**: building size preferred, land size fallback; PPSY = Leasehold PPSQ / remaining lease years.
- **Freehold PPSY**: optional horizon (default 30 years) divides price per SQM.
- **Lease years**: parsed from `lease_duration`, `lease_expiry_year`, or text regex (`xx years`).
- **Outliers**: metrics (price, PPSY, ADR, yield proxy) flagged outside P1-P99 for optional exclusion.

## 6. Known Limitations / Next Steps

- Geospatial outputs require `latitude`/`longitude`; falls back to ranking charts if absent.
- Company insights depend on `Company`/`listing_agency` naming consistency.
- Occupancy metrics rely on `occupancy` column when supplied; otherwise visuals degrade gracefully.
- Consider persisting computed aggregates (e.g., by region) or caching to reduce repeated groupby work for large datasets.

## 7. Running Checks

- Validate Python syntax / imports:

  ```bash
  venv/bin/python -m compileall src app.py
  ```

- Quick sanity check untuk pipeline enrichment:

  ```bash
  venv/bin/python scripts/validate_enrichment.py
  ```

- Streamlit warnings about `use_container_width` may appear when components are instantiated outside the Streamlit runtime (e.g., unit tests); safe to ignore in CLI checks.

Happy exploring Bali's property market!
