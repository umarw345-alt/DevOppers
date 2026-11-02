from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class SourceType(str, Enum):
    PDF_TEXT = "pdf_text"
    OCR = "ocr"


class Rectangle(BaseModel):
    x0: float
    y0: float
    x1: float
    y1: float


class WordToken(BaseModel):
    text: str
    confidence: float
    bounding_box: Rectangle
    page_number: int
    line_number: int | None = None
    block_number: int | None = None
    paragraph_number: int | None = None
    source: SourceType
    column: str | None = None
    font_size: float | None = None


class TextBlock(BaseModel):
    text: str
    confidence: float
    bounding_box: Rectangle
    page_number: int
    is_heading: bool = False
    words: list[WordToken] = Field(default_factory=list)
    source: SourceType
    column: str | None = None
    font_size: float | None = None


class FieldEvidence(BaseModel):
    field_name: str
    value: str | None = None
    confidence: float
    source_blocks: list[int] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
