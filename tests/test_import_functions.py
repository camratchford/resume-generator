import sys

import pytest

from resume_generator.import_functions import import_submodules


def test_broken_submodule_reraises_with_context(tmp_path, monkeypatch):
    """Regression test: import_submodules used to swallow every ImportError while
    discovering submodules, so a module with a genuine bug in it (as opposed to one
    that's simply missing) would just silently vanish from filter/extension
    discovery instead of surfacing a clear error.
    """
    package_dir = tmp_path / "broken_package"
    package_dir.mkdir()
    (package_dir / "__init__.py").write_text("")
    (package_dir / "broken_module.py").write_text("import this_module_does_not_exist\n")

    monkeypatch.syspath_prepend(str(tmp_path))
    sys.modules.pop("broken_package", None)
    sys.modules.pop("broken_package.broken_module", None)

    with pytest.raises(ImportError) as excinfo:
        import_submodules("broken_package")

    assert "broken_package.broken_module" in str(excinfo.value)
