from pathlib import Path
from typing import Annotated, Any

from sqlalchemy import Engine
from typer import Argument, Option, TyperException

from resume_generator.config import Config
from resume_generator.data import DBAccessor
from resume_generator.page_breaks import PageBreakMode
from resume_generator.ranking import CategoryRanker, PositionRanker, Ranker, load_profile
from resume_generator.resume import Model

TEMPLATES_PANEL = "Templates"
DIRECTORIES_PANEL = "Directories"
OUTPUT_PANEL = "Output"
RANKING_PANEL = "Ranking"
CONFIGURATION_PANEL = "Configuration"

OutputPathArgument = Annotated[
    Path,
    Argument(
        file_okay=True,
        dir_okay=True,
        help="Where to write the PDF. A path ending in '.pdf' is used as the file path. "
        "Any other path is treated as a directory, and the file is named '{document_name}.pdf'",
    ),
]
DocumentNameOption = Annotated[
    str | None,
    Option(
        "-n",
        "--document-name",
        help="Override the default document name and PDF title of '{candidate.name} - Resume'",
        rich_help_panel=OUTPUT_PANEL,
    ),
]
DryRunOption = Annotated[
    bool,
    Option("--dry-run", help="Do not write any files, only render in memory", rich_help_panel=OUTPUT_PANEL),
]
HTMLOutputOption = Annotated[
    bool,
    Option(
        "--html",
        help="Also write the intermediate HTML next to the PDF, with a '.html' extension",
        rich_help_panel=OUTPUT_PANEL,
    ),
]
MarkdownOutputOption = Annotated[
    bool,
    Option(
        "--markdown",
        help="Also write the intermediate Markdown next to the PDF, with a '.md' extension",
        rich_help_panel=OUTPUT_PANEL,
    ),
]
PDFKeywordsOption = Annotated[
    str,
    Option(
        "--keywords",
        help="Comma-separated keywords to add to the PDF metadata's keywords field",
        rich_help_panel=OUTPUT_PANEL,
    ),
]

TemplateNameOption = Annotated[
    str | None,
    Option(
        "-t",
        "--template-name",
        help="File name of the template to render, in the templates directory. Defaults to the profile's or "
        "config's template_name, then 'default.md'",
        rich_help_panel=TEMPLATES_PANEL,
    ),
]
TemplatePathOption = Annotated[
    Path | None,
    Option(
        "--template-path",
        file_okay=True,
        dir_okay=False,
        exists=True,
        help="Path to the template to render, from any directory",
        rich_help_panel=TEMPLATES_PANEL,
    ),
]
CSSStylesheetNameOption = Annotated[
    str | None,
    Option(
        "-s",
        "--css-stylesheet-name",
        help="File name of the CSS stylesheet to use, in the CSS directory. Defaults to the profile's or "
        "config's css_stylesheet_name, then 'default.css'",
        rich_help_panel=TEMPLATES_PANEL,
    ),
]
CSSStylesheetPathOption = Annotated[
    Path | None,
    Option(
        "--css-stylesheet-path",
        file_okay=True,
        dir_okay=False,
        exists=True,
        help="Path to the CSS stylesheet to use, from any directory",
        rich_help_panel=TEMPLATES_PANEL,
    ),
]

HomeDirOption = Annotated[
    Path | None,
    Option(
        "--home-dir",
        file_okay=False,
        dir_okay=True,
        exists=True,
        help="Directory containing the 'data', 'templates', and 'css' subdirectories. Defaults to ~/resume-generator",
        rich_help_panel=DIRECTORIES_PANEL,
    ),
]
CSSDirOption = Annotated[
    Path | None,
    Option(
        "--css-dir",
        file_okay=False,
        dir_okay=True,
        exists=True,
        help="Directory of CSS stylesheets. Defaults to {home_dir}/css",
        rich_help_panel=DIRECTORIES_PANEL,
    ),
]
DataDirOption = Annotated[
    Path | None,
    Option(
        "--data-dir",
        file_okay=False,
        dir_okay=True,
        exists=True,
        help="Directory of YAML data files. Defaults to {home_dir}/data",
        rich_help_panel=DIRECTORIES_PANEL,
    ),
]
TemplatesDirOption = Annotated[
    Path | None,
    Option(
        "--templates-dir",
        file_okay=False,
        dir_okay=True,
        exists=True,
        help="Directory of Jinja2 templates. Defaults to {home_dir}/templates",
        rich_help_panel=DIRECTORIES_PANEL,
    ),
]

ProfileNameOption = Annotated[
    str | None,
    Option(
        "-p",
        "--profile",
        help="Name of a profile in {home_dir}/profiles (without '.yml') whose ordered categories rank the details",
        rich_help_panel=RANKING_PANEL,
    ),
]
PageBreaksOption = Annotated[
    PageBreakMode | None,
    Option(
        "--page-breaks",
        case_sensitive=False,
        help="Where pages may break: 'off' (only explicit breaks), 'anywhere' (never strand a heading or split a "
        "bullet), or 'h2'/'h3'/'h4' (also keep each section at that heading level together). Defaults to h3",
        rich_help_panel=OUTPUT_PANEL,
    ),
]
CategoriesOption = Annotated[
    str,
    Option(
        "--categories",
        help="Comma-separated, ordered skill category names used to rank details. Overrides the profile's list",
        rich_help_panel=RANKING_PANEL,
    ),
]

ConfigPathOption = Annotated[
    Path | None,
    Option(
        "-c",
        "--config-path",
        file_okay=True,
        dir_okay=False,
        exists=True,
        help="Config file to load settings from. Defaults to {home_dir}/config.yml, if present",
        rich_help_panel=CONFIGURATION_PANEL,
    ),
]
ExtraConfigOption = Annotated[
    list[str],
    Option(
        "-o",
        "--option",
        help="Set any config value for this run, as 'key=value'. Repeatable",
        rich_help_panel=CONFIGURATION_PANEL,
    ),
]

MUTUALLY_EXCLUSIVE_PARAMS = (
    ("template_name", "template_path"),
    ("css_stylesheet_name", "css_stylesheet_path"),
)


def raise_on_mutually_exclusive_params(params: dict) -> None:
    for left_param, right_param in MUTUALLY_EXCLUSIVE_PARAMS:
        if params.get(left_param) and params.get(right_param):
            raise TyperException(f"Invalid parameters: '{left_param}' and '{right_param}' are mutually exclusive.")


def split_file_path(file_path: Path | None, directory: Path | None, file_name: str | None) -> tuple:
    if file_path is None:
        return directory, file_name
    return file_path.parent, file_path.name


def parse_extra_options(extra_options: list[str]) -> dict[str, str]:
    parsed = {}
    for option in extra_options:
        key, separator, value = option.partition("=")
        if not key or not separator or not value:
            raise TyperException(f"Invalid option syntax: Expecting key=value - got {option}")
        parsed[key] = value
    return parsed


def build_config_kwargs(
    config_path: Path | None,
    home_dir: Path | None,
    css_dir: Path | None,
    data_dir: Path | None,
    templates_dir: Path | None,
    extra_options: list[str],
) -> dict:
    paths = {
        "config_file": config_path,
        "manual_home_dir": home_dir,
        "manual_css_dir": css_dir,
        "manual_data_dir": data_dir,
        "manual_templates_dir": templates_dir,
    }
    return {**{key: path for key, path in paths.items() if path is not None}, **parse_extra_options(extra_options)}


def parse_category_names(categories: str) -> list[str]:
    return [name.strip() for name in categories.split(",") if name.strip()]


def parse_limit(name: str, value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError) as error:
        raise TyperException(f"'{name}' must be a whole number - got {value!r}") from error


def load_selected_profile(config: Config, profile_name: str | None) -> dict[str, Any]:
    if not profile_name:
        return {}
    try:
        return load_profile(config.profiles_dir, profile_name)
    except (FileNotFoundError, TypeError) as error:
        raise TyperException(str(error)) from error


def resolve_setting(option_value: Any, profile: dict[str, Any], config: Config, key: str) -> Any:
    return option_value or profile.get(key) or config.get(key)


def resolve_page_break_mode(config: Config, profile: dict[str, Any], mode: PageBreakMode | None) -> PageBreakMode:
    value = resolve_setting(mode, profile, config, "page_breaks")
    try:
        return PageBreakMode(str(getattr(value, "value", value)).lower())
    except ValueError as error:
        modes = ", ".join(page_break_mode.value for page_break_mode in PageBreakMode)
        raise TyperException(f"Unknown page_breaks mode {value!r}. Expected one of: {modes}") from error


def build_ranker(config: Config, profile: dict[str, Any], categories: str) -> Ranker:
    category_names = profile.get("categories", [])
    details_limit = parse_limit("bullets_per_job", profile.get("bullets_per_job", config.bullets_per_job))
    skills_limit = parse_limit("skills_per_job", profile.get("skills_per_job", config.skills_per_job))
    if categories:
        category_names = parse_category_names(categories)

    if not category_names:
        return PositionRanker(details_limit, skills_limit)
    return CategoryRanker(category_names, details_limit, skills_limit)


def raise_on_unknown_categories(ranker: Ranker, engine: Engine) -> None:
    category_names = getattr(ranker, "category_names", [])
    if not category_names:
        return

    with DBAccessor(base_model=Model, engine=engine) as db_accessor:
        known_names = {category.name for category in db_accessor["SkillCategory"]}
    unknown_names = [name for name in category_names if name not in known_names]
    if unknown_names:
        raise TyperException(
            f"Unknown skill categories: {', '.join(unknown_names)}. Known categories: {', '.join(sorted(known_names))}"
        )
