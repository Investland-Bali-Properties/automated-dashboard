# Real Estate Market Dashboard (Mini Version)

Streamlit dashboard visualizing cleaned real estate listings sourced from a Google Sheet (`[Silver]Unified_Clean_Data`). This is an initial minimal implementation (Market Overview + Property Explorer). Future pages will extend this foundation.

## Quick Start

1. Create a `.env` in project root:
```
SPREADSHEET_ID=your_google_sheet_id_here
SHEET_NAME=[Silver]Unified_Clean_Data
GOOGLE_APPLICATION_CREDENTIALS=google-credentials.json
```

2. Add `google-credentials.json` (service account). Share the target Google Sheet with the service account email.

3. Install dependencies:
```
pip install -r requirements.txt
```

4. Run the app:
```
streamlit run src/app.py
```

5. (Optional) Clear cached data via sidebar "Refresh Data" button.

## Current Features
- Google Sheets live data load (cached 10 min)
- Global sidebar filters: property type, area, price range, bedrooms
- KPI cards: total listings, median prices, median price per sqm
- Trend + distribution charts (Plotly)
- Paginated property explorer with clickable titles

## Project Structure
```
.streamlit/
  config.toml
src/
  app.py
  data/loader.py
  components/
    filters.py
    kpi_cards.py
    charts.py
  pages/
    market_overview.py
    property_explorer.py
requirements.txt
README.md
.env (not committed)
google-credentials.json (not committed)
```

## Roadmap
- Pricing Trends page (boxplots, rent vs sale comparisons)
- Supply & Demand page (availability, new listings over time)
- Company Insights page (broker performance, anomalies)
- Data Quality page (missing values, exchange rate checks)
- Reusable formatting + filter application utilities
- Unit tests for pure logic (filters, quality checks)
- Light theming & optional custom CSS

## Conventions
- Page funcs: `pages/<name>.py` -> `page_<name>(df)`
- Caching: `st.cache_data` only in data layer
- No heavy transformations here; upstream pipeline remains the source of truth

## Notes
If a column is missing, components degrade gracefully (show "N/A" or skip chart).
