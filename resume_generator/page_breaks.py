import re
from enum import Enum
from itertools import count
from typing import Any, Iterator, Sequence
from xml.etree import ElementTree

from markdown.extensions import Extension
from markdown.treeprocessors import Treeprocessor

HEADING_PATTERN = re.compile(r"^h([1-6])$")
DEEPEST_HEADING_LEVEL = 6
SECTION_CLASS = "page-break-section"

KEEP_TOGETHER_CSS = """h1, h2, h3, h4, h5, h6 { break-after: avoid; }
li, .row, .flex-wrap { break-inside: avoid; }
"""
SECTION_CSS = f"section.{SECTION_CLASS} {{ break-inside: avoid; }}\n"


class PageBreakMode(str, Enum):
    OFF = "off"
    ANYWHERE = "anywhere"
    H2 = "h2"
    H3 = "h3"
    H4 = "h4"

    @property
    def heading_level(self) -> int | None:
        if not self.value.startswith("h"):
            return None
        return int(self.value[1:])


def page_break_css(mode: PageBreakMode) -> str:
    if mode is PageBreakMode.OFF:
        return ""
    if mode.heading_level is None:
        return KEEP_TOGETHER_CSS
    return KEEP_TOGETHER_CSS + SECTION_CSS


def heading_level(element: ElementTree.Element) -> int | None:
    match = HEADING_PATTERN.match(element.tag) if isinstance(element.tag, str) else None
    return int(match.group(1)) if match else None


def wrap_sections(elements: Sequence[ElementTree.Element], level: int, section_ids: Iterator[int]) -> list:
    if level > DEEPEST_HEADING_LEVEL:
        return list(elements)

    wrapped = []
    section_elements = None
    for element in elements:
        found_level = heading_level(element)
        if found_level is not None and found_level <= level:
            if section_elements is not None:
                wrapped.append(build_section(section_elements, level, section_ids))
                section_elements = None
            if found_level == level:
                section_elements = [element]
                continue
        if section_elements is not None:
            section_elements.append(element)
        else:
            wrapped.append(element)

    if section_elements is not None:
        wrapped.append(build_section(section_elements, level, section_ids))
    return wrapped


def build_section(
    section_elements: Sequence[ElementTree.Element], level: int, section_ids: Iterator[int]
) -> ElementTree.Element:
    section = ElementTree.Element(
        "section", {"class": f"{SECTION_CLASS} level-{level}", "data-section": str(next(section_ids))}
    )
    heading, *content = section_elements
    section.append(heading)
    section.extend(wrap_sections(content, level + 1, section_ids))
    return section


class SectionWrapTreeprocessor(Treeprocessor):
    def __init__(self, md, level: int):
        super().__init__(md)
        self.level = level

    def run(self, root: ElementTree.Element) -> None:
        children = list(root)
        for child in children:
            root.remove(child)
        root.extend(wrap_sections(children, self.level, count()))


class SectionWrapExtension(Extension):
    """Wraps each heading of `level` or deeper, and the content under it, in a `<section>`."""

    def __init__(self, level: int, **kwargs):
        super().__init__(**kwargs)
        self.level = level

    def extendMarkdown(self, md):
        md.treeprocessors.register(SectionWrapTreeprocessor(md, self.level), "page_break_sections", 0)


def section_heights(document: Any) -> dict[str, float]:
    # WeasyPrint has no public API for laid-out boxes, so this reads each page's private box tree.
    heights = {}
    for page in document.pages:
        for box in page._page_box.descendants():
            element = box.element
            if element is not None and element.tag == "section" and element.get("data-section") is not None:
                section_id = element.get("data-section")
                heights[section_id] = heights.get(section_id, 0) + box.height
    return heights


def oversized_section_css(document: Any) -> str:
    if not document.pages:
        return ""
    page_height = document.pages[0]._page_box.height
    oversized = [section_id for section_id, height in section_heights(document).items() if height > page_height]
    return "".join(f'section[data-section="{section_id}"] {{ break-inside: auto; }}\n' for section_id in oversized)
