"""Pydantic models for code symbols and explanations."""

from typing import List

from pydantic import BaseModel, Field


class SymbolMetadata(BaseModel):
    """Metadata for a code symbol (class, function, or method)."""
    type: str
    name: str
    parent_class: str | None
    docstring: str | None
    start_line: int
    end_line: int
    file_path: str
    module_name: str
    source_code: str | None = None


class CodeExplanation(BaseModel):
    """Structured code explanation returned to user."""

    symbols: list[str] = Field(description="Symbols found")
    explanation: str = Field(description="Explanation of code")
    file_locations: list[str] = Field(description="File paths with line numbers")
    key_concepts: list[str] = Field(description="Key concepts")


class SymbolMatch(BaseModel):
    """Single symbol match with code and citation."""

    metadata: SymbolMetadata
    code: str
    citation: str


class SymbolLookupResult(BaseModel):
    """Lookup result with all matches and optional error."""

    matches: List[SymbolMatch] = []
    error: str | None = None
