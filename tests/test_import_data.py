import logging

from sqlmodel import Session, select

from resume_generator.config import Config
from resume_generator.db import initialize_db
from resume_generator.import_data import import_yaml_data
from resume_generator.resume import ALL_MODELS, Candidate


def test_every_model_is_imported(engine):
    with Session(engine) as session:
        for model in ALL_MODELS:
            assert session.exec(select(model)).all(), f"no rows imported for {model.__name__}"


def test_reimporting_is_idempotent(config, engine):
    import_yaml_data(engine, config)

    with Session(engine) as session:
        assert len(session.exec(select(Candidate)).all()) == 1


def test_in_memory_database_keeps_data_between_import_and_query(home_dir):
    config = Config(manual_home_dir=home_dir)
    engine = initialize_db(config)

    import_yaml_data(engine, config)

    with Session(engine) as session:
        assert session.exec(select(Candidate)).one().name == "Test Candidate"


def test_missing_data_file_is_skipped_with_a_warning(config, caplog):
    (config.data_dir / "hobby.yml").unlink()
    engine = initialize_db(config)

    with caplog.at_level(logging.WARNING):
        import_yaml_data(engine, config)

    assert "Hobby" in caplog.text
