import xml.etree.ElementTree as ElementTree

from markdown import Extension
from markdown.inlinepatterns import InlineProcessor

# Pattern to match %% content %%
FLEX_COLUMNS_RE = r"%%\s*(.*?)\s*%%"


class FlexColumnsInlineProcessor(InlineProcessor):
    def __init__(self, pattern, md=None):
        super().__init__(pattern, md)

    def handleMatch(self, match, data):
        # Extract the content between %% and %%
        content = match.group(1)

        columns = [col.strip() for col in content.split("||")]

        container = ElementTree.Element("div")
        container.set("class", "row")
        for col_text in columns:
            column = ElementTree.SubElement(container, "div")
            column.set("class", "column")
            column.text = col_text

        return container, match.start(0), match.end(0)


class FlexColumnsExtension(Extension):
    """Markdown extension for the `%% col1 || col2 || ... %%` inline syntax.

    Renders the given `||`-separated items as a `<div class="row">`
    containing one `<div class="column">` per item, for simple side-by-side
    layouts.
    """

    def extendMarkdown(self, md):
        processor = FlexColumnsInlineProcessor(FLEX_COLUMNS_RE, md)

        # Add with priority to ensure it runs before other inline processors
        md.inlinePatterns.register(processor, "columns", 175)


# noinspection PyPep8Naming
def makeExtension(**kwargs):
    return FlexColumnsExtension(**kwargs)
