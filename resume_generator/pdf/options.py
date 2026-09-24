from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator
from weasyprint import CSS, Attachment


class PDFOptions(BaseModel):
    """Typed wrapper around WeasyPrint's PDF rendering options.

    Mirrors the keyword arguments accepted by `weasyprint.HTML.render`/
    `weasyprint.Document.write_pdf` (see `weasyprint.DEFAULT_OPTIONS`), so an
    instance can be passed straight through via
    `model_dump(exclude_none=True)`.

    Attributes:
        stylesheets: Additional CSS to apply, as `weasyprint.CSS` objects or paths/URLs.
        attachments: Files to embed in the PDF as attachments.
        attachment_relationships: The PDF/A-3 AFRelationship value for attachments.
        pdf_identifier: The document's PDF identifier.
        pdf_variant: The target PDF variant (e.g. "pdf/a-3b", "pdf/ua-1").
        pdf_version: The target PDF version (e.g. "1.7").
        pdf_forms: Whether to keep interactive form fields in the output.
        pdf_tags: Whether to include structure tags for accessibility.
        uncompressed_pdf: Whether to disable PDF stream compression.
        xmp_metadata: Whether to include an XMP metadata stream.
        custom_metadata: Whether to include WeasyPrint's custom PDF metadata.
        presentational_hints: Whether to honor CSS presentational hints.
        output_intent: An ICC output intent identifier.
        optimize_images: Whether to re-encode images to reduce PDF size.
        jpeg_quality: JPEG re-encoding quality, clamped to 1-100.
        dpi: Maximum image resolution, in dots per inch.
        full_fonts: Whether to embed full font files instead of subsets.
        hinting: Whether to keep font hinting instructions.
        cache: A dict or path used to cache fetched resources across renders.
    """

    # weasprint.__init__.DEFAULT_OPTIONS
    model_config = ConfigDict(arbitrary_types_allowed=True)
    stylesheets: list[CSS | str] | None = None
    attachments: list[Attachment | str] | None = None
    attachment_relationships: str | None = None
    pdf_identifier: bytes | None = None
    pdf_variant: str | None = None
    pdf_version: str | None = None
    pdf_forms: bool | None = None
    pdf_tags: bool = False
    uncompressed_pdf: bool = False
    xmp_metadata: bool | None = None
    custom_metadata: bool = False
    presentational_hints: bool | None = None
    output_intent: str | None = None
    optimize_images: bool = False
    jpeg_quality: int | None = None
    dpi: int | None = None
    full_fonts: bool = False
    hinting: bool = False
    cache: dict[str, Any] | str | None = None

    @field_validator("jpeg_quality")
    @classmethod
    def clamp_jpeg_quality(cls, value: Any):
        if isinstance(value, int) and not (1 <= value <= 100):
            raise ValueError("jpeg_quality must be within range of 1-100")
        return value
