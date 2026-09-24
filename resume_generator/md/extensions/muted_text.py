import xml.etree.ElementTree as ElementTree

from markdown import Extension
from markdown.inlinepatterns import InlineProcessor

# Pattern to match %% content %%
MUTED_TEXT_RE = r"%m\s*(.*?)\s*m%"


class MutedTextInlineProcessor(InlineProcessor):
    def __init__(self, pattern, md=None):
        super().__init__(pattern, md)

    def handleMatch(self, match, data):
        # Extract the content between %m and m%
        content = match.group(1)

        # Create the container div
        container = ElementTree.Element("span")
        container.set("class", "muted-text")
        container.text = content.strip()

        return container, match.start(0), match.end(0)


class MutedTextExtension(Extension):
    """Markdown extension for the `%m text m%` inline syntax.

    Renders the enclosed text as a `<span class="muted-text">`, for
    de-emphasized inline text.
    """

    def extendMarkdown(self, md):
        processor = MutedTextInlineProcessor(MUTED_TEXT_RE, md)

        # Add with priority to ensure it runs before other inline processors
        md.inlinePatterns.register(processor, "muted_text", 175)


# noinspection PyPep8Naming
def makeExtension(**kwargs):
    return MutedTextExtension(**kwargs)
