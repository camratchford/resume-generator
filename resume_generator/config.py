from pathlib import Path
from typing import Any, Mapping

from byoconfig import Config as BYOConfig
from yaml import safe_load


class Config(BYOConfig):
    base_module: str = __name__.split(".")[0]
    app_name: str = base_module.replace("_", "-")
    env_prefix: str = base_module.upper()

    dry_run: bool = False
    variable_default_values: dict[str, Any] = {}

    bullets_per_job: int | None = None
    skills_per_job: int | None = None
    page_breaks: str = "h3"

    manual_home_dir: Path | None = None
    manual_templates_dir: Path | None = None
    manual_data_dir: Path | None = None
    manual_css_dir: Path | None = None

    @property
    def home_dir(self) -> Path:
        if self.manual_home_dir:
            return self.manual_home_dir

        return Path().home() / self.app_name

    pdf_keywords: list[str] = [
        "resume",
        "CV",
    ]

    db_url: str = "sqlite://"
    db_echo: bool = False

    @property
    def templates_dir(self):
        if self.manual_templates_dir:
            if not self.manual_templates_dir.is_dir():
                raise FileNotFoundError(f"User-provided templates_dir does not exist: {self.manual_templates_dir}")
            return self.manual_templates_dir

        if self.home_dir:
            return self.home_dir / "templates"

        return None

    @property
    def data_dir(self):
        if self.manual_data_dir:
            if not self.manual_data_dir.is_dir():
                raise FileNotFoundError(f"User-provided data_dir does not exist: {self.manual_data_dir}")
            return self.manual_data_dir

        if self.home_dir:
            return self.home_dir / "data"

        return None

    @property
    def profiles_dir(self):
        return self.home_dir / "profiles"

    @property
    def css_dir(self):
        if self.manual_css_dir:
            if not self.manual_css_dir.is_dir():
                raise FileNotFoundError(f"User-provided css_dir does not exist: {self.manual_css_dir}")
            return self.manual_css_dir

        if self.home_dir:
            return self.home_dir / "css"

        return None

    def parse_pdf_keywords(self, keyword_string: str):
        for keyword in keyword_string.split(","):
            keyword = keyword.strip()
            if keyword and keyword not in self.pdf_keywords:
                self.pdf_keywords.append(keyword)

    @staticmethod
    def get_missing_home_dir_subpaths(home_dir: Path):
        required_subpaths = ("templates", "data", "css")
        return [home_dir.joinpath(subpath) for subpath in required_subpaths if not home_dir.joinpath(subpath).exists()]

    @staticmethod
    def usable_config_file(config_file: Path | None) -> Path | None:
        if config_file is None:
            return None

        settings = safe_load(Path(config_file).read_text())
        if settings is None:
            return None
        if not isinstance(settings, Mapping):
            raise TypeError(
                f"Config file {config_file} must contain 'key: value' settings - got a {type(settings).__name__}"
            )
        return config_file

    def __init__(self, **kwargs):
        self.manual_home_dir = kwargs.get("manual_home_dir")
        pdf_keywords = kwargs.pop("pdf_keywords", "")
        if not self.home_dir.exists():
            raise FileNotFoundError("Config's home_dir value points to a path that does not exist.")
        else:
            missing_subpaths = self.get_missing_home_dir_subpaths(self.home_dir)
            if missing_subpaths:
                raise FileNotFoundError(
                    f"Config's home_dir value points to a path that does not contain all of the required "
                    f"subdirectories. Missing subdirectories: {', '.join(str(path) for path in missing_subpaths)}"
                )
            home_config_file = None
            found_config_files = [file for file in self.home_dir.glob("config.y*ml", case_sensitive=False)]
            if found_config_files:
                home_config_file = found_config_files.pop()

        config_file = self.usable_config_file(kwargs.get("config_file", home_config_file))
        super().__init__(**kwargs, env_prefix=self.env_prefix, file_path=config_file)
        self.pdf_keywords = list(self.pdf_keywords)
        self.parse_pdf_keywords(pdf_keywords)
