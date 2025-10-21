"""
Application-wide configuration constants and helper utilities.
"""

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class TabConfig:
    key: str
    label: str


# Ordered tab definitions for the dashboard
TABS: List[TabConfig] = [
    TabConfig("overview", "Overview"),
    TabConfig("sales_market", "Sales Market"),
    TabConfig("rental_market", "Rental Market (ADR & Occupancy)"),
    TabConfig("supply_velocity", "Supply & Velocity"),
    TabConfig("ownership_mix", "Ownership Mix"),
    TabConfig("off_plan_ready", "Off-plan vs Ready"),
    TabConfig("regional_insights", "Regional Insights"),
    TabConfig("data_source", "Data Source Insight"),
    TabConfig("explorer", "Explorer"),
    TabConfig("data_quality", "Data Quality & Definitions"),
]
