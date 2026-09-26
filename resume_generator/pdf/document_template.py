from typing import Any

from jinja2 import Environment

from resume_generator.pdf.metadata import PDFMetadata

BASE_HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="{{ language }}">
<head>
<title>{{ title }}</title>
<meta http-equiv="Content-type" content="text/html;charset=UTF-8">
{% for author in authors %}
<meta name="author" content="{{ author }}">
{% endfor %}
<meta name="generator" content="{{ generator }}">
<meta name="keywords" content="{{ keywords | join(",") }}">
<meta name="dcterms.created" content="{{ created.strftime('%Y-%m-%d') }}">
<meta name="dcterms.modified" content="{{ modified.strftime('%Y-%m-%d') }}">
<meta name="description" content="{{ description }}">
{% for key in custom %}
<meta name="{{ key }}" content="{{ custom[key] }}">
{% endfor %}
<style>
{{ css }}
</style>
</head>
<body>
<div class="markdown-container">
    {{ html }}
</div>
</body>
</html>
"""


def finalize(value: Any):
    return value if value is not None else ""


def render_document_html(html: str, css: str, metadata: PDFMetadata):
    jinja2_env = Environment(finalize=finalize)
    template_globals = {"html": html, "css": css, **metadata.model_dump()}

    return jinja2_env.from_string(BASE_HTML_TEMPLATE, globals=template_globals).render()
