from typer.testing import CliRunner

from resume_generator.__main__ import cli

runner = CliRunner()


def test_cli_generates_a_pdf(home_dir, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    out_dir = tmp_path / "out"

    result = runner.invoke(
        cli,
        [
            "render",
            str(out_dir),
            "--home-dir",
            str(home_dir),
            "-t",
            "resume.md",
            "-s",
            "resume.css",
            "--keywords",
            "",
        ],
    )

    assert result.exit_code == 0, result.output

    pdfs = list(out_dir.glob("*.pdf"))
    assert len(pdfs) == 1
    assert pdfs[0].read_bytes().startswith(b"%PDF")


def test_cli_generates_markdown_and_html_intermediaries(home_dir, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    out_dir = tmp_path / "out"

    result = runner.invoke(
        cli,
        [
            "render",
            str(out_dir),
            "--home-dir",
            str(home_dir),
            "-t",
            "resume.md",
            "-s",
            "resume.css",
            "--keywords",
            "",
            "--markdown",
            "--html",
        ],
    )

    assert result.exit_code == 0, result.output

    markdown_text = next(out_dir.glob("*.md")).read_text()
    assert "TEST CANDIDATE" in markdown_text
    assert "Test Engineer" in markdown_text
    assert "### Career Gap\n" in markdown_text
    assert "at None" not in markdown_text

    html_text = next(out_dir.glob("*.html")).read_text()
    assert html_text.lstrip().startswith("<!DOCTYPE html>")
    assert (home_dir / "css" / "resume.css").read_text() in html_text
    assert "break-inside: avoid" in html_text
    assert "<title>Test Candidate - Resume</title>" in html_text
    assert '<div class="row">' in html_text


def test_cli_writes_to_an_explicit_pdf_path(home_dir, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    out_file = tmp_path / "out" / "tailored.pdf"

    result = runner.invoke(
        cli,
        ["render", str(out_file), "--home-dir", str(home_dir), "-t", "resume.md", "-s", "resume.css"],
    )

    assert result.exit_code == 0, result.output
    assert out_file.read_bytes().startswith(b"%PDF")
    assert [path.name for path in out_file.parent.iterdir()] == ["tailored.pdf"]
