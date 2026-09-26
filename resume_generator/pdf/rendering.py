from pathlib import Path

from weasyprint import HTML
from weasyprint.text.fonts import FontConfiguration

from resume_generator.page_breaks import oversized_section_css
from resume_generator.pdf.document_template import render_document_html
from resume_generator.pdf.metadata import PDFMetadata
from resume_generator.pdf.options import PDFOptions


def render_document(
    html: str,
    css: str,
    pdf_metadata: PDFMetadata,
    pdf_options: PDFOptions,
    base_url: Path | None = None,
    relax_oversized_sections: bool = False,
    html_out_file: Path | None = None,
):
    options = pdf_options.model_dump(exclude_none=True)
    font_config = FontConfiguration()

    def layout(stylesheet: str):
        document_html = render_document_html(html=html, css=stylesheet, metadata=pdf_metadata)
        return HTML(string=document_html, base_url=base_url).render(font_config=font_config, **options), document_html

    document, document_html = layout(css)
    if relax_oversized_sections:
        relaxing_css = oversized_section_css(document)
        if relaxing_css:
            document, document_html = layout(css + relaxing_css)

    if html_out_file is not None:
        html_out_file.write_text(document_html)
    return document


def render_pdf(
    out_file: Path,
    html: str,
    css: str,
    pdf_metadata: PDFMetadata = None,
    pdf_options: PDFOptions = None,
    relax_oversized_sections: bool = False,
    html_out_file: Path | None = None,
):
    """Render HTML/CSS to a PDF file using WeasyPrint.

    Args:
        out_file: The path to write the rendered PDF to. Also used as the
            base URL for resolving relative resources in `html`, and as the
            default document title when `pdf_metadata` is not given.
        html: The document body as an HTML string.
        css: Additional CSS to apply to the document.
        pdf_metadata: Metadata to embed in the PDF. Defaults to a
            `PDFMetadata` titled after `out_file`'s filename.
        pdf_options: WeasyPrint rendering options. Defaults to `PDFOptions()`.
        relax_oversized_sections: Re-render with `break-inside: auto` on any
            page-break section taller than a page, so it breaks in place
            instead of first being pushed to a new page.
        html_out_file: If given, also write the complete HTML document that
            was laid out, including the stylesheet and metadata, to this path.
    """
    pdf_metadata = pdf_metadata or PDFMetadata(title=out_file.stem)
    pdf_options = pdf_options or PDFOptions()
    pdf_options.custom_metadata = bool(pdf_metadata.custom)

    document = render_document(html, css, pdf_metadata, pdf_options, out_file, relax_oversized_sections, html_out_file)
    document.write_pdf(target=out_file, **pdf_options.model_dump(exclude_none=True))
