"""Quick validation script for enrichment outputs.

Run with `python scripts/validate_enrichment.py` to ensure key columns
are produced and contain expected data types.
"""

from __future__ import annotations

import pandas as pd

from src.data.enrichment import enrich_listings


def main() -> None:
    sample = pd.DataFrame(
        {
            "listing_type": ["for sale", "for rent"],
            "price_idr": [500_000_000, 120_000_000],
            "sale_price_idr": [520_000_000, None],
            "rent_price_month_idr": [None, 10_000_000],
            "rent_period": [None, "monthly"],
            "building_size_sqm": [120, 80],
            "land_size_sqm": [200, 150],
            "ownership_type": ["Freehold", "Leasehold"],
            "lease_duration": [None, "25 years"],
            "listing_date": pd.to_datetime(["2024-04-01", "2024-05-15"]),
            "scraped_at": pd.to_datetime(["2024-06-01", "2024-06-02"]),
            "area": ["Canggu", "Seminyak"],
        }
    )

    enriched = enrich_listings(sample)
    required_cols = [
        "price_sale_idr",
        "rent_price_month_idr_norm",
        "price_per_sqm_idr_calc",
        "price_per_sqm_per_year",
        "adr_idr",
        "days_listed",
    ]

    missing = [col for col in required_cols if col not in enriched.columns]
    if missing:
        raise SystemExit(f"Missing required columns: {missing}")

    assert enriched["price_sale_idr"].notna().iloc[0], "Sale listing should populate price_sale_idr"
    assert enriched["rent_price_month_idr_norm"].notna().iloc[1], "Rent listing should normalise monthly rent"

    print("Enrichment validation passed. Rows:", len(enriched))


if __name__ == "__main__":
    main()
