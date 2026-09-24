from datetime import datetime
from pathlib import Path

from sqlalchemy import Engine

from resume_generator.config import Config
from resume_generator.data import DBAccessor
from resume_generator.md import create_markdown_renderer
from resume_generator.pdf import PDFMetadata, PDFOptions, render_pdf
from resume_generator.ranking import Ranker
from resume_generator.resume import Model
from resume_generator.templates import new_template_environment
from resume_generator.user_input import prompt_for_variable_values


def resolve_out_file(output_path: Path, document_name: str) -> Path:
    if output_path.suffix.lower() == ".pdf":
        return output_path
    return output_path / f"{document_name}.pdf"


def render_resume(
    template_name: str,
    css_stylesheet_name: str,
    document_name: str,
    output_path: Path,
    engine: Engine,
    config: Config,
    generate_html: bool,
    generate_markdown: bool,
    ranker: Ranker = None,
):
    with DBAccessor(base_model=Model, engine=engine) as db_accessor:
        candidates = db_accessor["Candidate"]
        if not candidates:
            raise IndexError("No Candidate instances exist in the database.")
        candidate_name = candidates[0].name
        document_name = document_name if document_name else f"{candidate_name} - Resume"

        out_file = resolve_out_file(output_path, document_name)
        if not config.dry_run:
            out_file.parent.mkdir(parents=True, exist_ok=True)

        jinja2_environment = new_template_environment(
            templates_dir=config.templates_dir,
            db_accessor=db_accessor,
            ranker=ranker,
        )

        markdown_template = jinja2_environment.get_template(template_name)
        if jinja2_environment.undeclared_variables:
            user_vars = prompt_for_variable_values(
                jinja2_environment.undeclared_variables, config.variable_default_values
            )
            db_accessor.update(user_vars)

        markdown = markdown_template.render()
        if generate_markdown and not config.dry_run:
            out_file.with_suffix(".md").write_text(markdown)

        html_renderer = create_markdown_renderer()
        html = html_renderer.convert(markdown)
        if generate_html and not config.dry_run:
            out_file.with_suffix(".html").write_text(html)

        css_path = config.css_dir.joinpath(css_stylesheet_name)
        css = css_path.read_text()

        now = datetime.now()
        metadata_kwargs = {
            "title": document_name,
            "generator": __name__.split(".")[0],
            "authors": [candidate_name],
            "created": now,
            "modified": now,
            "keywords": [*config.pdf_keywords, candidate_name],
            "language": "en-us",
            "description": f"{candidate_name}'s resume",
            "custom": {"Copyright": f"© {now.year} {candidate_name}"},
            **{k: v for k, v in config.get_by_prefix("metadata", trim_prefix=True).items() if v is not None},
        }

        pdf_metadata = PDFMetadata(**metadata_kwargs)
        pdf_options = PDFOptions(custom_metadata=True)
        if config.dry_run:
            out_file = None
        render_pdf(out_file=out_file, html=html, css=css, pdf_metadata=pdf_metadata, pdf_options=pdf_options)
