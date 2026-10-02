from pathlib import Path

import pytest
from typer.testing import CliRunner

from resume_generator.__main__ import cli

runner = CliRunner()

EXAMPLES_DIR = Path(__file__).parent.parent / "examples"
WIZARD_HOME = EXAMPLES_DIR / "wizard"
WIZARD_PROFILES = sorted(path.stem for path in (WIZARD_HOME / "profiles").glob("*.yml"))


@pytest.mark.parametrize("profile", WIZARD_PROFILES)
def test_wizard_example_renders_every_profile(profile, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(
        cli,
        ["render", str(tmp_path / "out"), "--home-dir", str(WIZARD_HOME), "--profile", profile, "--markdown"],
    )

    assert result.exit_code == 0, result.output
    markdown_text = next((tmp_path / "out").glob("*.md")).read_text()
    assert "IXAR EL'EDEL" in markdown_text
    assert "(None)" not in markdown_text
