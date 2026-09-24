from importlib.metadata import PackageNotFoundError, version

from .data import DataImporter, DBAccessor
from .md import create_markdown_renderer
from .pdf import PDFMetadata, PDFOptions, render_pdf
from .templates import TypedVariableEnvironment, new_template_environment
from .user_input import prompt_for_variable_values

try:
    __version__ = version("resume-generator")
except PackageNotFoundError:
    __version__ = "0.0.0"

__all__ = [
    "__version__",
    "DataImporter",
    "DBAccessor",
    "create_markdown_renderer",
    "PDFOptions",
    "PDFMetadata",
    "render_pdf",
    "new_template_environment",
    "TypedVariableEnvironment",
    "prompt_for_variable_values",
]
