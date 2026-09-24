import pytest
from typer.main import get_command
from typer.testing import CliRunner

from resume_generator import __main__ as main_module
from resume_generator.__main__ import cli
from resume_generator.ranking import CategoryRanker, PositionRanker

runner = CliRunner()


def test_main_command_options_have_unique_flags():
    """Regression test: __main__.py once had four options all bound to the literal
    string '--home-dir', and two bound to '-t'. Click silently routes a flag to
    whichever parameter registered it last, so the earlier ones were unreachable
    from the CLI with no error at startup.
    """
    click_command = get_command(cli).commands["render"]

    flag_owner = {}
    for param in click_command.params:
        for opt in param.opts:
            assert opt not in flag_owner, (
                f"Flag '{opt}' is registered on both '{flag_owner[opt]}' and '{param.name}' - "
                f"only the last-registered one is reachable from the CLI"
            )
            flag_owner[opt] = param.name


@pytest.fixture
def captured_render(monkeypatch):
    calls = []
    monkeypatch.setattr(main_module, "render_resume", lambda **kwargs: calls.append(kwargs))
    return calls


def invoke(home_dir, tmp_path, *extra_arguments):
    return runner.invoke(
        cli,
        ["render", str(tmp_path / "out"), "--home-dir", str(home_dir), *extra_arguments],
    )


def test_template_and_stylesheet_names_are_passed_through(home_dir, tmp_path, captured_render):
    result = invoke(home_dir, tmp_path, "-t", "resume.md", "-s", "resume.css", "-n", "Custom", "--html", "--markdown")

    assert result.exit_code == 0, result.output
    call = captured_render[0]
    assert call["template_name"] == "resume.md"
    assert call["css_stylesheet_name"] == "resume.css"
    assert call["document_name"] == "Custom"
    assert call["generate_html"] is True
    assert call["generate_markdown"] is True
    assert call["output_path"] == tmp_path / "out"


def test_template_path_sets_template_dir_and_name(home_dir, tmp_path, captured_render):
    template = tmp_path / "elsewhere" / "tailored.md"
    template.parent.mkdir()
    template.write_text("hello")

    result = invoke(home_dir, tmp_path, "--template-path", str(template), "-s", "resume.css")

    assert result.exit_code == 0, result.output
    assert captured_render[0]["template_name"] == "tailored.md"
    assert captured_render[0]["config"].templates_dir == template.parent


def test_css_stylesheet_path_sets_css_dir_and_name(home_dir, tmp_path, captured_render):
    stylesheet = tmp_path / "styles" / "tailored.css"
    stylesheet.parent.mkdir()
    stylesheet.write_text("body {}")

    result = invoke(home_dir, tmp_path, "-t", "resume.md", "--css-stylesheet-path", str(stylesheet))

    assert result.exit_code == 0, result.output
    assert captured_render[0]["css_stylesheet_name"] == "tailored.css"
    assert captured_render[0]["config"].css_dir == stylesheet.parent


@pytest.mark.parametrize(
    "flag, name", [("--templates-dir", "templates"), ("--data-dir", "data"), ("--css-dir", "css")]
)
def test_directory_overrides_reach_config(home_dir, tmp_path, captured_render, flag, name):
    override = tmp_path / f"custom-{name}"
    override.mkdir()
    if name == "data":
        for data_file in (home_dir / "data").iterdir():
            (override / data_file.name).write_text(data_file.read_text())

    result = invoke(home_dir, tmp_path, "-t", "resume.md", "-s", "resume.css", flag, str(override))

    assert result.exit_code == 0, result.output
    assert getattr(captured_render[0]["config"], f"{name}_dir") == override


def test_extra_options_are_set_on_config(home_dir, tmp_path, captured_render):
    result = invoke(home_dir, tmp_path, "-t", "resume.md", "-s", "resume.css", "-o", "metadata_title=Custom Title")

    assert result.exit_code == 0, result.output
    assert captured_render[0]["config"].get_by_prefix("metadata", trim_prefix=True) == {"title": "Custom Title"}


def test_extra_option_with_empty_value_is_rejected(home_dir, tmp_path, captured_render):
    result = invoke(home_dir, tmp_path, "-t", "resume.md", "-s", "resume.css", "-o", "metadata_title=")

    assert result.exit_code != 0
    assert "Invalid option syntax" in str(result.exception)


def test_extra_option_without_equals_sign_is_rejected_cleanly(home_dir, tmp_path, captured_render):
    result = invoke(home_dir, tmp_path, "-t", "resume.md", "-s", "resume.css", "-o", "metadata_title")

    assert "Invalid option syntax" in str(result.exception)


def test_dry_run_reaches_config(home_dir, tmp_path, captured_render):
    result = invoke(home_dir, tmp_path, "-t", "resume.md", "-s", "resume.css", "--dry-run")

    assert result.exit_code == 0, result.output
    assert captured_render[0]["config"].dry_run is True


def test_nonexistent_home_dir_is_rejected(tmp_path, captured_render):
    result = runner.invoke(cli, ["render", str(tmp_path / "out"), "--home-dir", str(tmp_path / "missing")])

    assert result.exit_code != 0
    assert captured_render == []


def test_template_name_and_template_path_are_mutually_exclusive(home_dir, tmp_path, captured_render):
    result = invoke(
        home_dir, tmp_path, "-t", "resume.md", "--template-path", str(home_dir / "templates" / "resume.md")
    )

    assert result.exit_code != 0


def test_config_path_is_loaded(home_dir, tmp_path, captured_render):
    config_file = tmp_path / "custom.yml"
    config_file.write_text("metadata_title: From Flag\n")

    result = invoke(home_dir, tmp_path, "-t", "resume.md", "-s", "resume.css", "-c", str(config_file))

    assert result.exit_code == 0, result.output
    assert captured_render[0]["config"].get_by_prefix("metadata", trim_prefix=True) == {"title": "From Flag"}


def test_default_ranker_keeps_data_order(home_dir, tmp_path, captured_render):
    result = invoke(home_dir, tmp_path, "-t", "resume.md", "-s", "resume.css")

    assert result.exit_code == 0, result.output
    assert isinstance(captured_render[0]["ranker"], PositionRanker)


def test_profile_supplies_categories_and_bullet_limit(home_dir, tmp_path, captured_render):
    result = invoke(home_dir, tmp_path, "-t", "resume.md", "-s", "resume.css", "--profile", "devops")

    assert result.exit_code == 0, result.output
    ranker = captured_render[0]["ranker"]
    assert isinstance(ranker, CategoryRanker)
    assert ranker.category_names == ["DevOps"]
    assert ranker.details_limit == 1
    assert ranker.skills_limit == 1


def test_categories_option_overrides_profile_categories(home_dir, tmp_path, captured_render):
    result = invoke(
        home_dir,
        tmp_path,
        "-t",
        "resume.md",
        "-s",
        "resume.css",
        "-p",
        "devops",
        "--categories",
        " Programming, DevOps ",
    )

    assert result.exit_code == 0, result.output
    ranker = captured_render[0]["ranker"]
    assert ranker.category_names == ["Programming", "DevOps"]
    assert ranker.details_limit == 1


def test_missing_profile_is_rejected_with_available_names(home_dir, tmp_path, captured_render):
    result = invoke(home_dir, tmp_path, "-t", "resume.md", "-s", "resume.css", "--profile", "nope")

    assert result.exit_code != 0
    assert "Available profiles: devops" in str(result.exception)
    assert captured_render == []


def test_unknown_category_is_rejected(home_dir, tmp_path, captured_render):
    result = invoke(home_dir, tmp_path, "-t", "resume.md", "-s", "resume.css", "--categories", "DevOps,Netwerking")

    assert result.exit_code != 0
    assert "Unknown skill categories: Netwerking" in str(result.exception)
    assert captured_render == []


def test_config_supplies_default_limits(home_dir, tmp_path, captured_render):
    (home_dir / "config.yml").write_text("bullets_per_job: 3\nskills_per_job: 5\n")

    result = invoke(home_dir, tmp_path, "-t", "resume.md", "-s", "resume.css")

    assert result.exit_code == 0, result.output
    ranker = captured_render[0]["ranker"]
    assert (ranker.details_limit, ranker.skills_limit) == (3, 5)


def test_profile_limits_override_config_limits(home_dir, tmp_path, captured_render):
    (home_dir / "config.yml").write_text("bullets_per_job: 3\nskills_per_job: 5\n")

    result = invoke(home_dir, tmp_path, "-t", "resume.md", "-s", "resume.css", "--profile", "devops")

    assert result.exit_code == 0, result.output
    ranker = captured_render[0]["ranker"]
    assert (ranker.details_limit, ranker.skills_limit) == (1, 1)


def test_extra_option_limit_is_converted_to_a_number(home_dir, tmp_path, captured_render):
    result = invoke(home_dir, tmp_path, "-t", "resume.md", "-s", "resume.css", "-o", "bullets_per_job=2")

    assert result.exit_code == 0, result.output
    assert captured_render[0]["ranker"].details_limit == 2


def test_non_numeric_limit_is_rejected(home_dir, tmp_path, captured_render):
    result = invoke(home_dir, tmp_path, "-t", "resume.md", "-s", "resume.css", "-o", "bullets_per_job=lots")

    assert result.exit_code != 0
    assert "'bullets_per_job' must be a whole number" in str(result.exception)
