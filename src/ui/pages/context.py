from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from src.data.filters import GlobalFilters


@dataclass
class PageContext:
    raw_df: pd.DataFrame
    enriched_df: pd.DataFrame
    filters: GlobalFilters
