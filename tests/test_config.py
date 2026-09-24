import pytest

from resume_generator.config import Config


def test_manual_home_dir_is_honored(home_dir):
    """Regression test: Config.home_dir was a fixed field that never read the
    manual_home_dir kwarg, and __init__ validated home_dir before super().__init__()
    had even assigned it - so --home-dir was silently ignored either way.
    """
    config = Config(manual_home_dir=home_dir)
    assert config.home_dir == home_dir


def test_missing_home_dir_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        Config(manual_home_dir=tmp_path / "does-not-exist")


def test_home_dir_missing_a_required_subdir_raises(tmp_path):
    incomplete_home = tmp_path / "incomplete-home"
    incomplete_home.mkdir()
    (incomplete_home / "data").mkdir()
    (incomplete_home / "templates").mkdir()
    # no "css" subdirectory

    with pytest.raises(FileNotFoundError):
        Config(manual_home_dir=incomplete_home)


def test_separate_config_instances_are_independent(home_dir, tmp_path):
    """Regression test: Config used to be a process-wide singleton, so a second
    Config(...) call returned the first instance's state regardless of new kwargs.
    """
    other_home = tmp_path / "other-home"
    other_home.mkdir()
    (other_home / "data").mkdir()
    (other_home / "templates").mkdir()
    (other_home / "css").mkdir()

    first = Config(manual_home_dir=home_dir)
    second = Config(manual_home_dir=other_home)

    assert first is not second
    assert first.home_dir != second.home_dir


def make_home(root):
    for subdirectory in ("data", "templates", "css"):
        (root / subdirectory).mkdir(parents=True)
    return root


def test_subdirectories_default_to_home_dir(home_dir):
    config = Config(manual_home_dir=home_dir)

    assert config.templates_dir == home_dir / "templates"
    assert config.data_dir == home_dir / "data"
    assert config.css_dir == home_dir / "css"


@pytest.mark.parametrize("name", ["templates", "data", "css"])
def test_manual_subdirectory_overrides_home_dir(home_dir, tmp_path, name):
    """Regression test: templates_dir and data_dir validated their manual override
    but then fell through to home_dir, so --templates-dir, --data-dir, and
    --template-path were silently ignored.
    """
    override = tmp_path / f"custom-{name}"
    override.mkdir()

    config = Config(manual_home_dir=home_dir, **{f"manual_{name}_dir": override})

    assert getattr(config, f"{name}_dir") == override


@pytest.mark.parametrize("name", ["templates", "data", "css"])
def test_nonexistent_manual_subdirectory_raises_file_not_found(home_dir, tmp_path, name):
    config = Config(manual_home_dir=home_dir, **{f"manual_{name}_dir": tmp_path / "missing"})

    with pytest.raises(FileNotFoundError):
        getattr(config, f"{name}_dir")


def test_default_db_url_is_in_memory(home_dir):
    assert Config(manual_home_dir=home_dir).db_url == "sqlite://"


def test_config_yml_in_home_dir_is_loaded(home_dir):
    (home_dir / "config.yml").write_text("db_echo: true\nmetadata_title: From Home\n")

    config = Config(manual_home_dir=home_dir)

    assert config.db_echo is True
    assert config.get_by_prefix("metadata", trim_prefix=True) == {"title": "From Home"}


def test_explicit_config_file_takes_precedence_over_home_config(home_dir, tmp_path):
    (home_dir / "config.yml").write_text("metadata_title: From Home\n")
    explicit_config = tmp_path / "explicit.yml"
    explicit_config.write_text("metadata_title: From Explicit\n")

    config = Config(manual_home_dir=home_dir, config_file=explicit_config)

    assert config.get_by_prefix("metadata", trim_prefix=True) == {"title": "From Explicit"}


def test_kwargs_override_defaults(home_dir):
    config = Config(manual_home_dir=home_dir, db_url="sqlite:///elsewhere.db", dry_run=True)

    assert config.db_url == "sqlite:///elsewhere.db"
    assert config.dry_run is True


def test_parse_pdf_keywords_appends_new_keywords_only(home_dir, monkeypatch):
    monkeypatch.setattr(Config, "pdf_keywords", ["resume", "CV"])
    config = Config(manual_home_dir=home_dir)
    starting_keywords = list(config.pdf_keywords)

    config.parse_pdf_keywords("devops, resume ,linux")

    assert config.pdf_keywords == [*starting_keywords, "devops", "linux"]


def test_pdf_keywords_kwarg_produces_a_keyword_list(home_dir):
    config = Config(manual_home_dir=home_dir, pdf_keywords="devops,linux")

    assert config.pdf_keywords == ["resume", "CV", "devops", "linux"]


def test_parse_pdf_keywords_does_not_leak_between_instances(home_dir, monkeypatch):
    monkeypatch.setattr(Config, "pdf_keywords", ["resume", "CV"])
    first = Config(manual_home_dir=home_dir)
    first.parse_pdf_keywords("only-on-first")

    second = Config(manual_home_dir=home_dir)

    assert "only-on-first" not in second.pdf_keywords


def test_empty_home_dir_with_all_subdirectories_is_valid(tmp_path):
    home = make_home(tmp_path / "bare-home")

    assert Config(manual_home_dir=home).home_dir == home


def test_limits_default_to_unlimited(home_dir):
    config = Config(manual_home_dir=home_dir)

    assert (config.bullets_per_job, config.skills_per_job) == (None, None)
