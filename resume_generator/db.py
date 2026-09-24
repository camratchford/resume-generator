from sqlmodel import create_engine

from resume_generator.config import Config
from resume_generator.resume.model import Model


def initialize_db(config: Config):
    engine = create_engine(**config.get_by_prefix("db", trim_prefix=True))
    Model.metadata.create_all(engine)

    return engine
