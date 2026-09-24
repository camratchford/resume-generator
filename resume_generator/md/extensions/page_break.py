from xml.etree import ElementTree

from markdown import Extension
from markdown.inlinepatterns import InlineProcessor

# Pattern to match %( content )%
PAGE_BREAK_RE = r"%:pg:%"


class PageBreakInlineProcessor(InlineProcessor):
    def __init__(self, pattern, md=None):
        super().__init__(pattern, md)

    def handleMatch(self, match, data):

        container = ElementTree.Element("div")
        container.set("class", "page")

        return container, match.start(0), match.end(0)


class PageBreakExtension(Extension):
    """Markdown extension for the `%:pg:%` inline syntax.

    Renders an empty `<div class="page">`, intended to be styled with a CSS
    page-break rule when rendering to PDF.
    """

    def extendMarkdown(self, md):

        processor = PageBreakInlineProcessor(PAGE_BREAK_RE, md)

        # Add with priority to ensure it runs before other inline processors
        md.inlinePatterns.register(processor, "page_break", 175)


# noinspection PyPep8Naming
def makeExtension(**kwargs):
    return PageBreakExtension(**kwargs)
