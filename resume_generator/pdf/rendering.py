from pathlib import Path

from weasyprint import HTML
from weasyprint.text.fonts import FontConfiguration

from resume_generator.pdf.document_template import render_document_html
from resume_generator.pdf.metadata import PDFMetadata
from resume_generator.pdf.options import PDFOptions


def render_pdf(
    out_file: Path,
    html: str,
    css: str,
    pdf_metadata: PDFMetadata = None,
    pdf_options: PDFOptions = None,
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
    """
    pdf_metadata = pdf_metadata or PDFMetadata(title=out_file.stem)
    pdf_options = pdf_options or PDFOptions()
    pdf_options.custom_metadata = bool(pdf_metadata.custom)

    font_config: FontConfiguration = FontConfiguration()

    document_html = render_document_html(html=html, css=css, metadata=pdf_metadata)
    options = pdf_options.model_dump(exclude_none=True)
    html = HTML(string=document_html, base_url=out_file)
    pdf_document = html.render(font_config=font_config, **options)
    pdf_document.write_pdf(target=out_file, **options)
