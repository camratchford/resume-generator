import shutil
from pathlib import Path

import pytest

from resume_generator.config import Config
from resume_generator.data import DBAccessor
from resume_generator.db import initialize_db
from resume_generator.import_data import import_yaml_data
from resume_generator.resume import Model

FIXTURES_HOME = Path(__file__).parent / "fixtures" / "home"


@pytest.fixture
def home_dir(tmp_path):
    dest = tmp_path / "home"
    shutil.copytree(FIXTURES_HOME, dest)
    return dest


@pytest.fixture
def config(tmp_path, home_dir):
    return Config(
        manual_home_dir=home_dir,
        db_url=f"sqlite:///{tmp_path / 'test.db'}",
    )


@pytest.fixture
def engine(config):
    engine = initialize_db(config)
    import_yaml_data(engine, config)
    return engine


@pytest.fixture
def accessor(engine):
    with DBAccessor(base_model=Model, engine=engine) as db_accessor:
        yield db_accessor
