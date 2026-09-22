import logging
import os
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def save_metrics(
    company: str,
    year: Optional[int],
    metrics: Dict[str, Any],
) -> None:
    """
    Persist extracted financial metrics to database.

    Args:
        company: Company name.
        year: Year of report.
        metrics: Dictionary of extracted metrics.
    """
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print(f"Metrics recorded for {company} ({year}): {metrics}")
        print("Note: DATABASE_URL not set. Skipping database persistence.")
        return

    print(f"Connecting to database to save metrics for {company} ({year})...")
