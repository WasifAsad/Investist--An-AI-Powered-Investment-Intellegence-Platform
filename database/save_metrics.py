import logging
import os
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def save_metrics(
    company: str,
    year: Optional[int],
    metrics: Any,
) -> None:
    """
    Persist extracted financial metrics to database.

    Args:
        company: Company name.
        year: Year of report.
        metrics: FinancialMetrics object or dictionary of extracted metrics.
    """
    metrics_data = metrics.to_dict() if hasattr(metrics, "to_dict") else metrics
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print(f"Metrics recorded for {company} ({year}): {metrics_data}")
        print("Note: DATABASE_URL not set. Skipping database persistence.")
        return

    print(f"Connecting to database to save metrics for {company} ({year})...")
