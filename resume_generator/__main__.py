import logging

from typer import Context, Typer

from resume_generator.cli import (
    CategoriesOption,
    ConfigPathOption,
    CSSDirOption,
    CSSStylesheetNameOption,
    CSSStylesheetPathOption,
    DataDirOption,
    DocumentNameOption,
    DryRunOption,
    ExtraConfigOption,
    HomeDirOption,
    HTMLOutputOption,
    MarkdownOutputOption,
    OutputPathArgument,
    PDFKeywordsOption,
    ProfileNameOption,
    TemplateNameOption,
    TemplatePathOption,
    TemplatesDirOption,
    build_config_kwargs,
    build_ranker,
    raise_on_mutually_exclusive_params,
    raise_on_unknown_categories,
    split_file_path,
)
from resume_generator.config import Config
from resume_generator.db import initialize_db
from resume_generator.import_data import import_yaml_data
from resume_generator.render_resume import render_resume

logger = logging.getLogger(__name__)
cli = Typer(pretty_exceptions_enable=False)


# Makes the app a command group, so `render` stays a subcommand instead of Typer running it as the whole app.
@cli.callback()
def callback():
    pass


@cli.command()
def render(
    ctx: Context,
    output_path: OutputPathArgument,
    document_name: DocumentNameOption = None,
    template_name: TemplateNameOption = None,
    template_path: TemplatePathOption = None,
    css_stylesheet_name: CSSStylesheetNameOption = None,
    css_stylesheet_path: CSSStylesheetPathOption = None,
    home_dir: HomeDirOption = None,
    css_dir: CSSDirOption = None,
    data_dir: DataDirOption = None,
    templates_dir: TemplatesDirOption = None,
    profile_name: ProfileNameOption = None,
    categories: CategoriesOption = "",
    config_path: ConfigPathOption = None,
    extra_options: ExtraConfigOption = (),
    dry_run: DryRunOption = False,
    html_output: HTMLOutputOption = False,
    markdown_output: MarkdownOutputOption = False,
    pdf_keywords: PDFKeywordsOption = "",
):
    raise_on_mutually_exclusive_params(ctx.params)
    templates_dir, template_name = split_file_path(template_path, templates_dir, template_name)
    css_dir, css_stylesheet_name = split_file_path(css_stylesheet_path, css_dir, css_stylesheet_name)

    config_kwargs = build_config_kwargs(config_path, home_dir, css_dir, data_dir, templates_dir, extra_options)
    config = Config(**config_kwargs, dry_run=dry_run, pdf_keywords=pdf_keywords)

    db_engine = initialize_db(config)
    import_yaml_data(db_engine, config)
    ranker = build_ranker(config, profile_name, categories)
    raise_on_unknown_categories(ranker, db_engine)

    render_resume(
        template_name=template_name,
        css_stylesheet_name=css_stylesheet_name,
        output_path=output_path,
        document_name=document_name,
        engine=db_engine,
        config=config,
        generate_html=html_output,
        generate_markdown=markdown_output,
        ranker=ranker,
    )


if __name__ == "__main__":
    cli()
