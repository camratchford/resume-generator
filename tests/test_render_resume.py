import pytest
from sqlmodel import create_engine

from resume_generator import render_resume as render_resume_module
from resume_generator.config import Config
from resume_generator.db import initialize_db
from resume_generator.import_data import import_yaml_data
from resume_generator.ranking import CategoryRanker
from resume_generator.render_resume import render_resume
from resume_generator.resume import Model


@pytest.fixture
def captured_pdf_calls(monkeypatch):
    calls = []
    monkeypatch.setattr(render_resume_module, "render_pdf", lambda **kwargs: calls.append(kwargs))
    return calls


def load_engine(home_dir, tmp_path, **config_kwargs):
    config = Config(manual_home_dir=home_dir, db_url=f"sqlite:///{tmp_path / 'test.db'}", **config_kwargs)
    engine = initialize_db(config)
    import_yaml_data(engine, config)
    return config, engine


def render(config, engine, output_path, **overrides):
    arguments = {
        "template_name": "resume.md",
        "css_stylesheet_name": "resume.css",
        "document_name": None,
        "output_path": output_path,
        "engine": engine,
        "config": config,
        "generate_html": False,
        "generate_markdown": False,
        **overrides,
    }
    render_resume(**arguments)


def test_default_document_name_uses_candidate_name(config, engine, tmp_path, captured_pdf_calls):
    render(config, engine, tmp_path / "out")

    assert captured_pdf_calls[0]["out_file"] == tmp_path / "out" / "Test Candidate - Resume.pdf"
    assert captured_pdf_calls[0]["pdf_metadata"].title == "Test Candidate - Resume"


def test_document_name_override(config, engine, tmp_path, captured_pdf_calls):
    render(config, engine, tmp_path, document_name="Custom")

    assert captured_pdf_calls[0]["out_file"] == tmp_path / "Custom.pdf"


def test_output_directory_is_created(config, engine, tmp_path, captured_pdf_calls):
    render(config, engine, tmp_path / "nested" / "out")

    assert (tmp_path / "nested" / "out").is_dir()


def test_stylesheet_is_read_from_css_dir(config, engine, tmp_path, captured_pdf_calls):
    render(config, engine, tmp_path)

    assert captured_pdf_calls[0]["css"] == (config.css_dir / "resume.css").read_text()


def test_metadata_includes_candidate_and_keywords(config, engine, tmp_path, captured_pdf_calls):
    render(config, engine, tmp_path)

    metadata = captured_pdf_calls[0]["pdf_metadata"]
    assert metadata.authors == ["Test Candidate"]
    assert "Test Candidate" in metadata.keywords
    assert "resume" in metadata.keywords


def test_metadata_prefixed_config_values_override_defaults(home_dir, tmp_path, captured_pdf_calls):
    (home_dir / "config.yml").write_text("metadata_title: Overridden Title\n")
    config, engine = load_engine(home_dir, tmp_path)

    render(config, engine, tmp_path)

    assert captured_pdf_calls[0]["pdf_metadata"].title == "Overridden Title"


def test_markdown_and_html_intermediaries(config, engine, tmp_path, captured_pdf_calls):
    render(config, engine, tmp_path, generate_markdown=True, generate_html=True)

    markdown = (tmp_path / "Test Candidate - Resume.md").read_text()
    html = (tmp_path / "Test Candidate - Resume.html").read_text()
    assert "# TEST CANDIDATE" in markdown
    assert "<h1>TEST CANDIDATE</h1>" in html
    assert captured_pdf_calls[0]["html"] == html


def test_dry_run_writes_no_files(home_dir, tmp_path, captured_pdf_calls):
    config, engine = load_engine(home_dir, tmp_path, dry_run=True)
    output_path = tmp_path / "out"

    render(config, engine, output_path, generate_markdown=True, generate_html=True)

    assert not output_path.exists()
    assert captured_pdf_calls[0]["out_file"] is None


@pytest.mark.parametrize("file_name", ["resume.pdf", "resume.PDF"])
def test_pdf_output_path_is_used_as_the_file(config, engine, tmp_path, captured_pdf_calls, file_name):
    render(config, engine, tmp_path / "nested" / file_name, generate_markdown=True)

    assert captured_pdf_calls[0]["out_file"] == tmp_path / "nested" / file_name
    assert (tmp_path / "nested" / "resume.md").is_file()


def test_non_pdf_suffix_is_treated_as_a_directory(config, engine, tmp_path, captured_pdf_calls):
    render(config, engine, tmp_path / "applications.v2")

    assert captured_pdf_calls[0]["out_file"] == tmp_path / "applications.v2" / "Test Candidate - Resume.pdf"


def test_pdf_output_path_keeps_the_default_document_title(config, engine, tmp_path, captured_pdf_calls):
    render(config, engine, tmp_path / "resume.pdf")

    assert captured_pdf_calls[0]["pdf_metadata"].title == "Test Candidate - Resume"


def test_missing_candidate_raises(config, tmp_path, captured_pdf_calls):
    empty_engine = create_engine("sqlite://")
    Model.metadata.create_all(empty_engine)

    with pytest.raises(IndexError, match="No Candidate"):
        render(config, empty_engine, tmp_path)


def test_undeclared_template_variables_are_prompted_for(config, engine, tmp_path, captured_pdf_calls, monkeypatch):
    (config.templates_dir / "cover.md").write_text("Dear {{ hiring_manager }}, {{ years: int }} years")
    prompted = {}

    def fake_prompt(variables, defaults):
        prompted.update(variables)
        return {"hiring_manager": "Ada", "years": 8}

    monkeypatch.setattr(render_resume_module, "prompt_for_variable_values", fake_prompt)

    render(config, engine, tmp_path, template_name="cover.md", generate_markdown=True)

    assert prompted == {"hiring_manager": str, "years": int}
    assert (tmp_path / "Test Candidate - Resume.md").read_text() == "Dear Ada, 8 years"


def test_template_without_undeclared_variables_does_not_prompt(
    config, engine, tmp_path, captured_pdf_calls, monkeypatch
):
    def fail_prompt(*args, **kwargs):
        raise AssertionError("should not prompt")

    monkeypatch.setattr(render_resume_module, "prompt_for_variable_values", fail_prompt)

    render(config, engine, tmp_path)


def test_category_ranking_reorders_and_limits_rendered_bullets(config, engine, tmp_path, captured_pdf_calls):
    render(config, engine, tmp_path, generate_markdown=True, ranker=CategoryRanker(["DevOps"], details_limit=1))

    markdown = (tmp_path / "Test Candidate - Resume.md").read_text()
    assert "- Automated test infrastructure." in markdown
    assert "- Did testing things." not in markdown


def test_default_rendering_keeps_every_bullet_in_data_order(config, engine, tmp_path, captured_pdf_calls):
    render(config, engine, tmp_path, generate_markdown=True)

    markdown = (tmp_path / "Test Candidate - Resume.md").read_text()
    assert markdown.index("- Did testing things.") < markdown.index("- Automated test infrastructure.")


def test_category_ranking_reorders_skill_bubbles(config, engine, tmp_path, captured_pdf_calls):
    render(config, engine, tmp_path, generate_markdown=True, ranker=CategoryRanker(["IaC"]))

    markdown = (tmp_path / "Test Candidate - Resume.md").read_text()
    assert "%( Terraform||Python )%" in markdown
