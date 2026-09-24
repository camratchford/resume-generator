import logging
from pathlib import Path
from typing import Annotated

from typer import Argument, Context, Option, Typer, TyperException

from resume_generator.config import Config
from resume_generator.db import initialize_db
from resume_generator.import_data import import_yaml_data
from resume_generator.render_resume import render_resume

logger = logging.getLogger(__name__)
cli = Typer(pretty_exceptions_enable=False)


MUTUALLY_EXCLUSIVE_PARAMS = (
    (
        "template_name",
        "template_path",
    ),
    (
        "css_stylesheet_name",
        "css_stylesheet_path",
    ),
)


@cli.callback()
def callback():
    pass


def raise_on_mutually_exclusive_params(params: dict):
    for left_param, right_param in MUTUALLY_EXCLUSIVE_PARAMS:
        if params.get(left_param) and params.get(right_param):
            raise TyperException(f"Invalid parameters: '{left_param}' and '{right_param}' are mutually exclusive.")


@cli.command()
def main(
    ctx: Context,
    output_path: Annotated[
        Path,
        Argument(
            file_okay=True,
            dir_okay=True,
            help="The path that the output PDF document should be written to. "
            "A path ending in '.pdf' is used as the file path. "
            "Any other path is treated as a directory, and the file is named '{document_name}.pdf'",
        ),
    ],
    document_name: Annotated[
        str,
        Option(
            "-n",
            "--document-name",
            help="Override the default PDF metadata field from '{candidate.name} - resume' to this",
        ),
    ] = None,
    config_path: Annotated[
        Path | None,
        Option(
            "-c",
            "--config-path",
            file_okay=True,
            dir_okay=False,
            help="Path to a config file used to load configuration defaults",
        ),
    ] = None,
    home_dir: Annotated[
        Path | None,
        Option(
            "--home-dir",
            file_okay=False,
            dir_okay=True,
            exists=True,
            help="A directory containing the 'data' and 'templates' subdirectory. "
            "Defaults to the current working directory.",
        ),
    ] = None,
    css_dir: Annotated[
        Path | None,
        Option(
            "--css-dir",
            file_okay=False,
            dir_okay=True,
            exists=True,
            help="Manually specify the location of your CSS stylesheet directory. Defaults to {home_dir}/css",
        ),
    ] = None,
    data_dir: Annotated[
        Path | None,
        Option(
            "--data-dir",
            file_okay=False,
            dir_okay=True,
            exists=True,
            help="Manually specify the location of your YAML data file directory. Defaults to {home_dir}/data",
        ),
    ] = None,
    templates_dir: Annotated[
        Path,
        Option(
            "--templates-dir",
            file_okay=False,
            dir_okay=True,
            exists=True,
            help="Manually specify the location of your Jinja2 templates directory. Defaults to {home_dir}/templates",
        ),
    ] = None,
    template_name: Annotated[
        str,
        Option(
            "-t",
            "--template-name",
            help="The file name of the template which will be rendered. Must be in the template_dir directory",
        ),
    ] = None,
    template_path: Annotated[
        Path,
        Option(
            "--template-path",
            file_okay=True,
            dir_okay=False,
            exists=True,
            help="The absolute path to the template you wish to render",
        ),
    ] = None,
    css_stylesheet_name: Annotated[
        str,
        Option(
            "-s",
            "--css-stylesheet-name",
            help="The file name of the CSS stylesheet which will be used. Must be in the css_dir directory",
        ),
    ] = None,
    css_stylesheet_path: Annotated[
        Path,
        Option(
            "--css-stylesheet-path",
            file_okay=True,
            dir_okay=False,
            exists=True,
            help="The absolute path to the CSS stylesheet you wish to use",
        ),
    ] = None,
    extra_options: Annotated[
        list[str],
        Option(
            "-o",
            "--option",
            help="Extra options (see README's 'Extra Options' section. Ex. -o 'key=value'",
        ),
    ] = (),
    dry_run: Annotated[
        bool,
        Option(
            "--dry-run",
            help="Do not generate any files, only render text objects in memory.",
        ),
    ] = False,
    html_output: Annotated[
        bool,
        Option(
            "--html",
            help="Write HTML intermediary file to disk."
            "Will share same path as output_path, except with the file extension of '.html' instead of '.pdf'",
        ),
    ] = False,
    markdown_output: Annotated[
        bool,
        Option(
            "--markdown",
            help="Write Markdown intermediary file to disk."
            "Will share same path as output_path, except with the file extension of '.md' instead of '.pdf'",
        ),
    ] = False,
    pdf_keywords: Annotated[
        str,
        Option(
            "--keywords", help="Comma-separated list of keywords to appear in the keywords field of the PDF Metadata"
        ),
    ] = "",
):
    raise_on_mutually_exclusive_params(ctx.params)

    config_kwargs = {}
    if config_path and config_path.exists():
        config_kwargs.update(config_file=config_path)
    if home_dir and home_dir.exists():
        config_kwargs.update(manual_home_dir=home_dir)
    if css_dir and css_dir.exists():
        config_kwargs.update(manual_css_dir=css_dir)
    if data_dir and data_dir.exists():
        config_kwargs.update(manual_data_dir=data_dir)
    if templates_dir and templates_dir.exists():
        config_kwargs.update(manual_templates_dir=templates_dir)
    if template_path and template_path.is_file():
        config_kwargs.update(manual_templates_dir=template_path.parent)
        template_name = template_path.name
    if css_stylesheet_path and css_stylesheet_path.is_file():
        config_kwargs.update(manual_css_dir=css_stylesheet_path.parent)
        css_stylesheet_name = css_stylesheet_path.name
    if extra_options:
        for option in extra_options:
            key, separator, value = option.partition("=")
            if not key or not separator or not value:
                raise TyperException(f"Invalid option syntax: Expecting key=value - got {option}")
            config_kwargs[key] = value

    config = Config(**config_kwargs, dry_run=dry_run, pdf_keywords=pdf_keywords)

    db_engine = initialize_db(config)
    import_yaml_data(db_engine, config)

    render_resume(
        template_name=template_name,
        css_stylesheet_name=css_stylesheet_name,
        output_path=output_path,
        document_name=document_name,
        engine=db_engine,
        config=config,
        generate_html=html_output,
        generate_markdown=markdown_output,
    )


if __name__ == "__main__":
    cli()
