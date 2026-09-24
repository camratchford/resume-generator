from xml.etree import ElementTree

from markdown import Extension
from markdown.inlinepatterns import InlineProcessor

# Pattern to match %( content )%
FLEX_WRAP_RE = r"%\(\s*(.*?)\s*\)%"


class FlexWrapInlineProcessor(InlineProcessor):
    def __init__(self, pattern, md=None):
        super().__init__(pattern, md)

    def handleMatch(self, match, data):
        # Extract the content between %( and )%
        content = match.group(1)

        # Split on || to get individual items
        items = [item.strip() for item in content.split("||")]

        # Create the container div
        container = ElementTree.Element("div")
        container.set("class", "flex-wrap")

        # Create each item as a bubble
        for item_text in items:
            if item_text:  # Only create bubbles for non-empty items
                bubble = ElementTree.SubElement(container, "div")
                bubble.set("class", "bubble")
                bubble.text = item_text

        return container, match.start(0), match.end(0)


class FlexWrapExtension(Extension):
    """Markdown extension for the `%( item1 || item2 || ... )%` inline syntax.

    Renders the given `||`-separated items as a `<div class="flex-wrap">`
    containing one `<div class="bubble">` per non-empty item, for wrapping
    lists of tags/badges.
    """

    def extendMarkdown(self, md):
        processor = FlexWrapInlineProcessor(FLEX_WRAP_RE, md)

        # Add with priority to ensure it runs before other inline processors
        md.inlinePatterns.register(processor, "flex_wrap", 175)


# noinspection PyPep8Naming
def makeExtension(**kwargs):
    return FlexWrapExtension(**kwargs)
