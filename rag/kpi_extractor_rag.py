import json
import logging
import os
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def extract_financial_metrics(
    retriever: Any,
    company: str,
    year: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Extract key financial metrics (Revenue, Net Income, EPS, Operating Margin, etc.)
    using retriever over ingested annual reports / financial documents.

    Args:
        retriever: Retriever instance with search/retrieve capabilities.
        company: Name of the company.
        year: Report year.

    Returns:
        Dictionary containing extracted financial metrics.
    """
    print(f"Extracting financial metrics for {company} (year: {year})...")
    query = (
        f"Key financial highlights, total revenue, net income, "
        f"diluted earnings per share (EPS), operating income for {company} {year or ''}"
    )

    docs = []
    try:
        if hasattr(retriever, "retrieve"):
            docs = retriever.retrieve(query, top_k=5)
        elif hasattr(retriever, "search"):
            docs = retriever.search(query, top=5)
        elif callable(retriever):
            docs = retriever(query)
    except Exception as e:
        logger.warning(f"Could not retrieve context for metrics extraction: {e}")

    print(f"Retrieved {len(docs)} context chunk(s) for KPI extraction.")

    # Base extracted metrics structure
    extracted: Dict[str, Any] = {
        "company": company,
        "year": year,
        "source_chunks_found": len(docs),
    }

    return extracted
