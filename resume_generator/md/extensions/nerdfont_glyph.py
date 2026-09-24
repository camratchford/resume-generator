from xml.etree import ElementTree

from markdown import Extension
from markdown.inlinepatterns import InlineProcessor

GLYPH_RE = r"%\+(\S)\+%"


class NerdfontGlyphInlineProcessor(InlineProcessor):
    def __init__(self, pattern, md=None):
        super().__init__(pattern, md)

    def handleMatch(self, match, data):

        container = ElementTree.Element("span")
        container.set("class", "nf")
        container.text = match.group(1)

        return container, match.start(0), match.end(0)


class NerdfontGlyphExtension(Extension):
    """Markdown extension for the `%+<glyph>+%` inline syntax.

    Renders the single enclosed character as a `<span class="nf">`, for
    embedding a Nerd Font icon glyph inline.
    """

    def extendMarkdown(self, md):

        processor = NerdfontGlyphInlineProcessor(GLYPH_RE, md)
        md.inlinePatterns.register(processor, "nerdfont_glyph", 175)


# noinspection PyPep8Naming
def makeExtension(**kwargs):
    return NerdfontGlyphExtension(**kwargs)
