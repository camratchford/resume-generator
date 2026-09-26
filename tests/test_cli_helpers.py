from pathlib import Path

import pytest
from typer import TyperException

from resume_generator.cli import (
    build_config_kwargs,
    parse_category_names,
    parse_extra_options,
    resolve_setting,
    split_file_path,
)
from resume_generator.config import Config


def test_split_file_path_prefers_the_full_path():
    assert split_file_path(Path("/a/b/tailored.md"), Path("/default"), "resume.md") == (Path("/a/b"), "tailored.md")


def test_split_file_path_keeps_directory_and_name_without_a_path():
    assert split_file_path(None, Path("/default"), "resume.md") == (Path("/default"), "resume.md")


def test_parse_extra_options():
    assert parse_extra_options(["metadata_title=My Title", "db_echo=true"]) == {
        "metadata_title": "My Title",
        "db_echo": "true",
    }


def test_parse_extra_options_keeps_equals_signs_in_values():
    assert parse_extra_options(["db_url=sqlite:///a=b.db"]) == {"db_url": "sqlite:///a=b.db"}


@pytest.mark.parametrize("option", ["no_equals", "=value", "key="])
def test_parse_extra_options_rejects_malformed_options(option):
    with pytest.raises(TyperException, match="Invalid option syntax"):
        parse_extra_options([option])


def test_build_config_kwargs_skips_unset_paths_and_lets_extra_options_win():
    config_kwargs = build_config_kwargs(
        config_path=None,
        home_dir=Path("/home"),
        css_dir=None,
        data_dir=None,
        templates_dir=Path("/templates"),
        extra_options=["manual_home_dir=/override"],
    )

    assert config_kwargs == {"manual_home_dir": "/override", "manual_templates_dir": Path("/templates")}


def test_parse_category_names_trims_and_drops_blanks():
    assert parse_category_names(" Networking, ,IoT ,") == ["Networking", "IoT"]


def test_resolve_setting_prefers_option_then_profile_then_config(home_dir):
    config = Config(manual_home_dir=home_dir, template_name="config.md")

    assert resolve_setting("option.md", {"template_name": "profile.md"}, config, "template_name") == "option.md"
    assert resolve_setting(None, {"template_name": "profile.md"}, config, "template_name") == "profile.md"
    assert resolve_setting(None, {}, config, "template_name") == "config.md"
