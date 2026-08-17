"""Small reporting helpers for the public repository.

The validated audit logic lives in audit_functions.py. This module is intentionally
small: it keeps recruiter-facing summaries separate from the analytical tests.
"""

def money(value: float) -> str:
    """Format a number as U.S. currency for lightweight public summaries."""
    return f"${value:,.2f}"
