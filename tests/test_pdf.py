from datetime import datetime

import pytest
from PIL import Image
from pydantic import ValidationError

from resume_generator.page_breaks import SECTION_CSS
from resume_generator.pdf import PDFMetadata, PDFOptions, render_document, render_pdf
from resume_generator.pdf.document_template import render_document_html


def test_metadata_strips_commas_from_keywords():
    metadata = PDFMetadata(keywords=["devops, linux", "python"])

    assert metadata.keywords == ["devops linux", "python"]


def test_metadata_defaults():
    metadata = PDFMetadata()

    assert metadata.language == "en-us"
    assert metadata.keywords == []
    assert isinstance(metadata.created, datetime)


@pytest.mark.parametrize("quality", [1, 50, 100, None])
def test_options_accept_valid_jpeg_quality(quality):
    assert PDFOptions(jpeg_quality=quality).jpeg_quality == quality


@pytest.mark.parametrize("quality", [0, 101])
def test_options_reject_out_of_range_jpeg_quality(quality):
    with pytest.raises(ValidationError):
        PDFOptions(jpeg_quality=quality)


def test_options_dump_omits_unset_values():
    options = PDFOptions().model_dump(exclude_none=True)

    assert "dpi" not in options
    assert options["custom_metadata"] is False


def test_document_html_wraps_body_css_and_metadata():
    metadata = PDFMetadata(
        title="My Resume",
        authors=["Test Candidate"],
        keywords=["resume", "devops"],
        description="A resume",
        created=datetime(2024, 5, 6),
        custom={"Copyright": "2024 Test Candidate"},
    )

    document = render_document_html(html="<p>body</p>", css="body { color: red; }", metadata=metadata)

    assert "<title>My Resume</title>" in document
    assert '<meta name="author" content="Test Candidate">' in document
    assert '<meta name="keywords" content="resume,devops">' in document
    assert '<meta name="dcterms.created" content="2024-05-06">' in document
    assert '<meta name="Copyright" content="2024 Test Candidate">' in document
    assert "body { color: red; }" in document
    assert "<p>body</p>" in document


def test_document_html_renders_missing_metadata_as_empty():
    document = render_document_html(html="", css="", metadata=PDFMetadata(title=None))

    assert "<title></title>" in document
    assert "None" not in document


def test_render_pdf_writes_a_pdf(tmp_path):
    out_file = tmp_path / "resume.pdf"

    render_pdf(out_file=out_file, html="<h1>Hello</h1>", css="")

    assert out_file.read_bytes().startswith(b"%PDF")


def test_render_pdf_enables_custom_metadata_only_when_present(tmp_path):
    options = PDFOptions(custom_metadata=True)

    render_pdf(out_file=tmp_path / "resume.pdf", html="", css="", pdf_metadata=PDFMetadata(), pdf_options=options)

    assert options.custom_metadata is False


def test_render_pdf_can_write_the_complete_html_document(tmp_path):
    html_file = tmp_path / "resume.html"

    render_pdf(
        out_file=tmp_path / "resume.pdf",
        html="<h1>Hello</h1>",
        css="h1 { color: red; }",
        pdf_metadata=PDFMetadata(title="My Resume"),
        html_out_file=html_file,
    )

    document = html_file.read_text()
    assert "<title>My Resume</title>" in document
    assert "h1 { color: red; }" in document
    assert "<h1>Hello</h1>" in document


def test_written_html_includes_css_added_by_the_second_page_break_pass(tmp_path):
    filler = "".join(f"<p>paragraph {index} " + "filler text " * 12 + "</p>" for index in range(60))
    html = f'<section class="page-break-section level-3" data-section="0"><h3>Huge</h3>{filler}</section>'
    html_file = tmp_path / "resume.html"

    render_document(
        html, SECTION_CSS, PDFMetadata(), PDFOptions(), relax_oversized_sections=True, html_out_file=html_file
    )

    assert 'section[data-section="0"] { break-inside: auto; }' in html_file.read_text()


def test_document_html_declares_the_metadata_language():
    document = render_document_html(html="", css="", metadata=PDFMetadata(title="My Resume", language="en-ca"))

    assert '<html lang="en-ca">' in document


def test_document_html_includes_a_base_href_only_when_given():
    with_base = render_document_html(html="", css="", metadata=PDFMetadata(), base_href="file:///home/css/resume.css")
    without_base = render_document_html(html="", css="", metadata=PDFMetadata())

    assert '<base href="file:///home/css/resume.css">' in with_base
    assert "<base" not in without_base


def loaded_images(document):
    return [
        box
        for page in document.pages
        for box in page._page_box.descendants()
        if type(box).__name__.endswith("ReplacedBox")
    ]


def test_relative_urls_resolve_against_the_base_url(tmp_path):
    (tmp_path / "css").mkdir()
    (tmp_path / "images").mkdir()
    Image.new("RGB", (4, 4), "red").save(tmp_path / "images" / "dot.png")
    stylesheet = tmp_path / "css" / "resume.css"
    stylesheet.write_text("")
    html = '<img src="../images/dot.png" alt="missing">'

    resolved = render_document(html, "", PDFMetadata(), PDFOptions(), base_url=stylesheet)
    unresolved = render_document(
        html, "", PDFMetadata(), PDFOptions(), base_url=tmp_path / "out" / "nested" / "resume.pdf"
    )

    assert len(loaded_images(resolved)) == 1
    assert loaded_images(unresolved) == []
