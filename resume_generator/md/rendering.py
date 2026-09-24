from typing import Sequence

from markdown import Markdown
from markdown.extensions import Extension

from resume_generator.import_functions import import_submodules


def create_markdown_renderer(
    *markdown_extensions_modules: str, extra_extensions: Sequence[Extension] = ()
) -> Markdown:
    """Build a `markdown.Markdown` renderer with resume_generator's extensions enabled.

    Discovers and registers every extension module under
    `resume_generator.md.extensions` and `pymdownx` (any submodule exposing a
    `makeExtension` callable), plus any additional extension modules passed
    in.

    Args:
        *markdown_extensions_modules: Additional dotted module paths to
            search for extensions exposing a `makeExtension` callable.
        extra_extensions: Already-configured extension instances to add, for
            extensions that need arguments and so can't be discovered.

    Returns:
        A configured `markdown.Markdown` instance.
    """
    markdown_extensions = import_submodules("resume_generator.md.extensions", has_attr_filter="makeExtension")
    markdown_extensions.update(import_submodules("pymdownx", has_attr_filter="makeExtension"))
    for extension_dir in markdown_extensions_modules:
        if not isinstance(extension_dir, str):
            continue

        markdown_extensions.update(import_submodules(extension_dir, has_attr_filter="makeExtension"))

    return Markdown(extensions=[*markdown_extensions, *extra_extensions])
