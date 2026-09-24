import logging

from sqlalchemy.engine import Engine

from resume_generator.config import Config
from resume_generator.data import DataImporter
from resume_generator.resume import ALL_MODELS, Model

logger = logging.getLogger(__name__)


def import_yaml_data(engine: Engine, config: Config):
    for model in ALL_MODELS:
        file_path = config.data_dir / (model.__tablename__ + ".yml")
        if not file_path.exists():
            logger.warning(f"Missing data file for model '{model.__name__}'")
            continue

        with DataImporter(base_model=Model, engine=engine) as data_importer:
            data_importer.load_data(file_path.read_text(), model)
