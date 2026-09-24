import pytest
from markdown import Markdown

from resume_generator.page_breaks import (
    KEEP_TOGETHER_CSS,
    SECTION_CSS,
    PageBreakMode,
    SectionWrapExtension,
    page_break_css,
)
from resume_generator.pdf import PDFMetadata, PDFOptions, render_document

PAGE_CSS = "@page { size: Letter; margin: 0.5in; } body { font-size: 12pt; } p { margin: 0 0 6pt 0; }"


def convert(markdown_text, level):
    return Markdown(extensions=[SectionWrapExtension(level)]).convert(markdown_text)


@pytest.mark.parametrize("mode, level", [("off", None), ("anywhere", None), ("h2", 2), ("h3", 3), ("h4", 4)])
def test_modes_map_to_heading_levels(mode, level):
    assert PageBreakMode(mode).heading_level == level


def test_unknown_mode_is_rejected():
    with pytest.raises(ValueError):
        PageBreakMode("h1")


def test_page_break_css_by_mode():
    assert page_break_css(PageBreakMode.OFF) == ""
    assert page_break_css(PageBreakMode.ANYWHERE) == KEEP_TOGETHER_CSS
    assert page_break_css(PageBreakMode.H3) == KEEP_TOGETHER_CSS + SECTION_CSS


def test_sections_wrap_each_heading_and_its_content():
    html = convert("## Work\n\n### Job A\n\nA text\n\n### Job B\n\nB text\n", 3)

    first_section, second_section = html.split("<section")[1:]
    assert html.count('class="page-break-section level-3"') == 2
    assert "<h2>Work</h2>" in html.split("<section")[0]
    assert "A text" in first_section and "B text" not in first_section
    assert "B text" in second_section


def test_section_ends_at_the_next_heading_of_the_same_or_higher_level():
    html = convert("### Job A\n\nA text\n\n## Projects\n\nIntro\n", 3)

    section, after = html.split("</section>", 1)
    assert "A text" in section
    assert "<h2>Projects</h2>" in after
    assert "Intro" in after


def test_deeper_headings_are_nested_inside_their_parent_section():
    html = convert("### Job\n\nSummary\n\n#### Duties\n\n- one\n\n#### Skills\n\ntools\n", 3)

    assert html.count("level-3") == 1
    assert html.count("level-4") == 2
    assert html.index("level-3") < html.index("level-4")


def test_content_before_the_first_heading_is_left_unwrapped():
    html = convert("Intro paragraph\n\n### Job\n\nText\n", 3)

    assert html.startswith("<p>Intro paragraph</p>")


def test_sections_get_unique_ids():
    html = convert("### A\n\n#### A1\n\ntext\n\n### B\n\ntext\n", 3)

    assert [f'data-section="{index}"' in html for index in range(3)] == [True, True, True]


def paragraphs(prefix, count):
    return "\n\n".join(f"{prefix} paragraph {index} " + "filler text " * 12 for index in range(count))


def layout_pages(markdown_text, mode, relax=False):
    mode = PageBreakMode(mode)
    extensions = [SectionWrapExtension(mode.heading_level)] if mode.heading_level else []
    html = Markdown(extensions=extensions).convert(markdown_text)
    document = render_document(
        html, page_break_css(mode) + PAGE_CSS, PDFMetadata(), PDFOptions(), relax_oversized_sections=relax
    )
    pages = {}
    for index, page in enumerate(document.pages):
        for box in page._page_box.descendants():
            text = "".join(box.element.itertext()) if box.element is not None and box.element.tag == "h3" else None
            if text:
                pages.setdefault(text, set()).add(index)
            if box.element is not None and box.element.tag == "p":
                pages.setdefault(box.element.text.split(" paragraph")[0], set()).add(index)
    return document, pages


TWO_SECTIONS = f"### First\n\n{paragraphs('first', 10)}\n\n### Second\n\n{paragraphs('second', 10)}\n"


def test_without_page_breaks_a_section_splits_across_pages():
    _, pages = layout_pages(TWO_SECTIONS, "off")

    assert len(pages["second"]) > 1


def test_h3_mode_keeps_each_h3_section_on_one_page():
    _, pages = layout_pages(TWO_SECTIONS, "h3", relax=True)

    assert len(pages["first"]) == 1
    assert len(pages["second"]) == 1
    assert pages["Second"] == pages["second"]


def test_oversized_section_breaks_in_place_instead_of_moving_to_a_new_page():
    markdown_text = f"### Intro\n\n{paragraphs('intro', 3)}\n\n### Huge\n\n{paragraphs('huge', 40)}\n"

    _, strict_pages = layout_pages(markdown_text, "h3", relax=False)
    _, relaxed_pages = layout_pages(markdown_text, "h3", relax=True)

    assert min(strict_pages["Huge"]) == 1
    assert min(relaxed_pages["Huge"]) == 0
