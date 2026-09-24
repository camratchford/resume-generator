from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


class PDFMetadata(BaseModel):
    """Document metadata to embed in a rendered PDF.

    Attributes:
        title: The document title.
        description: The document description/subject.
        generator: The name of the tool that generated the document.
        language: The document's language tag (e.g. "en-us").
        keywords: Keywords describing the document. Commas are stripped from
            each entry, since WeasyPrint uses commas to separate keywords.
        authors: The document's author names.
        created: The document's creation timestamp.
        modified: The document's last-modified timestamp.
        custom: Additional custom metadata fields.
    """

    title: str | None = None
    description: str | None = None
    generator: str | None = None
    language: str | None = "en-us"
    keywords: list[str] | None = []
    authors: list[str] | None = []
    created: datetime | None = Field(default_factory=datetime.now)
    modified: datetime | None = Field(default_factory=datetime.now)
    custom: dict | None = {}

    @field_validator("keywords")
    @classmethod
    def sanitize_for_commas(cls, value: Any):
        if isinstance(value, list):
            return [list_item.replace(",", "") for list_item in value]
        return value
