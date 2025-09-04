# Automated Dashboard (Dummy)

A Streamlit multipage dashboard using the theme in `.streamlit/config.toml` and dummy data.

## Run locally

- Create venv and install requirements
- Start Streamlit app

Commands (PowerShell):

```powershell
python -m venv .venv; . .venv/Scripts/Activate.ps1; pip install -r requirements.txt; streamlit run src/dashboard/dashboard.py
```

## Pages

1. Overview
2. Pricing Analytics (Sale)
3. Rental Analytics
4. Supply Explorer
5. Regional Heatmap
6. Competitor Insights
7. Data Quality & Freshness
8. Settings / Export

All pages use global filters in the sidebar and operate on dummy generated data.
