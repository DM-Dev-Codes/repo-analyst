"""Input validation utilities for API endpoints."""

import re
from fastapi import HTTPException

MAX_QUERY_LENGTH = 300

FORBIDDEN_PATTERNS = {
    "ignore previous",
    "disregard",
    "forget",
    "instead",
    "new instructions",
    "system:",
    "assistant:",
    "you are now",
    "act as",
    "pretend",
    "roleplay",
}


def validate_query(text: str) -> str:
    """Validate user query for security and format.
    
    Args:
        text: User query string
        
    Returns:
        Validated query string
        
    Raises:
        HTTPException: If query fails validation
    """
    if len(text) > MAX_QUERY_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Query too long. Max {MAX_QUERY_LENGTH} characters.",
        )

    if re.search(r'\.\.|/etc/|~/|file://', text.lower()):
        raise HTTPException(
            status_code=400,
            detail="Invalid characters detected.",
        )

    lower_text = text.lower()
    if any(pattern in lower_text for pattern in FORBIDDEN_PATTERNS):
        raise HTTPException(
            status_code=400,
            detail="Invalid query content detected.",
        )

    return text
