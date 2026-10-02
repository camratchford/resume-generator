from datetime import date

import pytest
from sqlmodel import Session, create_engine, select

from resume_generator.data import DataImporter
from resume_generator.resume import Candidate, Experience, Model, Project, Skill, SkillCategory


def _make_engine(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}")
    Model.metadata.create_all(engine)
    return engine


def test_reimporting_a_relationship_merges_instead_of_replacing(tmp_path):
    """Regression test: _upsert used to replace a relationship collection wholesale
    on every import, so re-importing a Skill with only ONE of its categories would
    silently drop the others. Real data hit this - Terraform, MSSQL, SCCM, and WDS
    all appeared twice in skill.yml with different category lists.
    """
    engine = _make_engine(tmp_path)

    with DataImporter(base_model=Model, engine=engine) as importer:
        importer.load_data("- name: DevOps\n- name: Linux\n", SkillCategory)

    with DataImporter(base_model=Model, engine=engine) as importer:
        importer.load_data("- name: Terraform\n  categories:\n    - name: DevOps\n", Skill)

    with DataImporter(base_model=Model, engine=engine) as importer:
        importer.load_data("- name: Terraform\n  categories:\n    - name: Linux\n", Skill)

    with Session(engine) as session:
        terraform = session.get(Skill, {"name": "Terraform"})
        assert {category.name for category in terraform.categories} == {"DevOps", "Linux"}


def test_duplicate_item_within_one_import_does_not_crash(tmp_path):
    """Regression test: a relationship list with the same primary key listed twice
    in a single YAML entry (e.g. a skill appearing twice under one experience) used
    to raise a sqlite3.IntegrityError on first creation, since the duplicate was
    never deduplicated before being assigned to the collection. Real data hit this -
    the Shell experience listed "Ansible" twice.
    """
    engine = _make_engine(tmp_path)

    with DataImporter(base_model=Model, engine=engine) as importer:
        importer.load_data("- name: Ansible\n", SkillCategory)

    with DataImporter(base_model=Model, engine=engine) as importer:
        importer.load_data("- name: Ansible\n  categories: []\n", Skill)

    with DataImporter(base_model=Model, engine=engine) as importer:
        importer.load_data(
            """
- canonical_name: test-co-engineer
  company: Test Co
  title: Engineer
  date_from: 2020-01-01
  location: Testville
  candidate_name: Test Candidate
  details:
    - canonical_name: test-co-automation
      description: test
      skills:
        - name: Ansible
        - name: Ansible
""",
            Experience,
        )

    with Session(engine) as session:
        experience = session.get(Experience, {"canonical_name": "test-co-engineer"})
        assert [skill.name for skill in experience.skills] == ["Ansible"]


def test_rejects_non_engine():
    with pytest.raises(TypeError):
        DataImporter(base_model=Model, engine="sqlite://")


def test_top_level_mapping_is_rejected(tmp_path):
    engine = _make_engine(tmp_path)

    with DataImporter(base_model=Model, engine=engine) as importer:
        with pytest.raises(TypeError, match="Sequence"):
            importer.load_data("name: Python\n", Skill)


def test_unknown_field_is_rejected(tmp_path):
    engine = _make_engine(tmp_path)

    with DataImporter(base_model=Model, engine=engine) as importer:
        with pytest.raises(KeyError, match="favourite_colour"):
            importer.load_data("- name: Python\n  favourite_colour: blue\n", Skill)


def test_scalar_given_for_a_list_field_is_rejected(tmp_path):
    engine = _make_engine(tmp_path)

    with DataImporter(base_model=Model, engine=engine) as importer:
        with pytest.raises(TypeError, match="expected Sequence"):
            importer.load_data("- name: Python\n  categories: 5\n", Skill)


def test_non_scalar_given_for_a_scalar_field_is_rejected(tmp_path):
    engine = _make_engine(tmp_path)

    with DataImporter(base_model=Model, engine=engine) as importer:
        with pytest.raises(TypeError, match="Candidate.email"):
            importer.load_data("- name: Test\n  email: [a, b]\n", Candidate)


def test_scalars_are_coerced_to_the_declared_type(tmp_path):
    engine = _make_engine(tmp_path)

    with DataImporter(base_model=Model, engine=engine) as importer:
        importer.load_data("- name: Test\n  telephone: 15551234567\n", Candidate)

    with Session(engine) as session:
        assert session.get(Candidate, {"name": "Test"}).telephone == "15551234567"


def test_null_scalars_stay_null_instead_of_becoming_the_string_none(tmp_path):
    engine = _make_engine(tmp_path)

    with DataImporter(base_model=Model, engine=engine) as importer:
        importer.load_data("- name: Test\n  telephone: null\n", Candidate)

    with Session(engine) as session:
        assert session.get(Candidate, {"name": "Test"}).telephone is None


def test_date_strings_are_coerced_to_dates(tmp_path):
    engine = _make_engine(tmp_path)

    with DataImporter(base_model=Model, engine=engine) as importer:
        importer.load_data(
            """
- canonical_name: job
  company: Test Co
  title: Engineer
  location: Testville
  candidate_name: Test Candidate
  date_from: '2020-01-01'
  date_to: null
""",
            Experience,
        )

    with Session(engine) as session:
        experience = session.get(Experience, {"canonical_name": "job"})
        assert experience.date_from == date(2020, 1, 1)
        assert experience.date_to is None


def test_reimporting_updates_scalars_without_duplicating_rows(tmp_path):
    engine = _make_engine(tmp_path)

    with DataImporter(base_model=Model, engine=engine) as importer:
        importer.load_data("- name: Test\n  email: old@example.com\n", Candidate)

    with DataImporter(base_model=Model, engine=engine) as importer:
        importer.load_data("- name: Test\n  email: new@example.com\n", Candidate)

    with Session(engine) as session:
        candidates = session.exec(select(Candidate)).all()
        assert [candidate.email for candidate in candidates] == ["new@example.com"]


def test_related_rows_are_created_on_first_reference(tmp_path):
    engine = _make_engine(tmp_path)

    with DataImporter(base_model=Model, engine=engine) as importer:
        importer.load_data("- name: Python\n  categories:\n    - name: Programming\n", Skill)

    with Session(engine) as session:
        assert session.get(SkillCategory, {"name": "Programming"}) is not None


def test_empty_relationship_list_is_accepted(tmp_path):
    engine = _make_engine(tmp_path)

    with DataImporter(base_model=Model, engine=engine) as importer:
        importer.load_data("- name: Python\n  categories: []\n", Skill)

    with Session(engine) as session:
        assert session.get(Skill, {"name": "Python"}).categories == []


def test_load_data_from_file(tmp_path):
    engine = _make_engine(tmp_path)
    data_file = tmp_path / "skill.yml"
    data_file.write_text("- name: Python\n- name: Bash\n")

    with DataImporter(base_model=Model, engine=engine) as importer:
        importer.load_data_from_file(data_file, Skill)

    with Session(engine) as session:
        assert {skill.name for skill in session.exec(select(Skill)).all()} == {"Python", "Bash"}


def test_fixture_home_imports_every_relationship(engine):
    with Session(engine) as session:
        project = session.get(Project, {"canonical_name": "test-project"})
        hobby_project = session.get(Project, {"canonical_name": "hobby-project"})
        python = session.get(Skill, {"name": "Python"})

        assert project.experience.canonical_name == "test-co-engineer"
        assert project.category.name == "Professional"
        assert hobby_project.hobby.canonical_name == "tinkering"
        assert {category.name for category in python.categories} == {"DevOps", "Programming"}


NESTED_EXPERIENCE = """
- canonical_name: job
  company: Test Co
  title: Engineer
  location: Testville
  date_from: 2020-01-01
  candidate_name: Test Candidate
  details:
    - canonical_name: job-first
      description: First bullet
      skills:
        - name: Python
        - name: Bash
    - canonical_name: job-second
      description: Second bullet
      skills:
        - name: Python
"""


def test_nested_details_are_imported_with_their_skills(tmp_path):
    engine = _make_engine(tmp_path)

    with DataImporter(base_model=Model, engine=engine) as importer:
        importer.load_data(NESTED_EXPERIENCE, Experience)

    with Session(engine) as session:
        experience = session.get(Experience, {"canonical_name": "job"})
        assert [detail.canonical_name for detail in experience.details] == ["job-first", "job-second"]
        assert [skill.name for skill in experience.details[0].skills] == ["Python", "Bash"]


def test_new_skill_shared_by_two_nested_details_is_created_once(tmp_path):
    """Regression test: _upsert only looked in the database for an existing row, so
    two details in one entry that both referenced a not-yet-imported skill each
    created their own Skill instance, raising a UNIQUE constraint error on commit.
    """
    engine = _make_engine(tmp_path)

    with DataImporter(base_model=Model, engine=engine) as importer:
        importer.load_data(NESTED_EXPERIENCE, Experience)

    with Session(engine) as session:
        assert [skill.name for skill in session.exec(select(Skill)).all()] == ["Python", "Bash"]


def test_reimporting_nested_details_does_not_duplicate_them(tmp_path):
    engine = _make_engine(tmp_path)

    for _ in range(2):
        with DataImporter(base_model=Model, engine=engine) as importer:
            importer.load_data(NESTED_EXPERIENCE, Experience)

    with Session(engine) as session:
        experience = session.get(Experience, {"canonical_name": "job"})
        assert [detail.canonical_name for detail in experience.details] == ["job-first", "job-second"]


def test_nested_details_get_their_yaml_position(tmp_path):
    engine = _make_engine(tmp_path)

    with DataImporter(base_model=Model, engine=engine) as importer:
        importer.load_data(NESTED_EXPERIENCE, Experience)

    with Session(engine) as session:
        experience = session.get(Experience, {"canonical_name": "job"})
        assert [(detail.canonical_name, detail.position) for detail in experience.details] == [
            ("job-first", 0),
            ("job-second", 1),
        ]


def test_explicit_positions_override_yaml_order(tmp_path):
    engine = _make_engine(tmp_path)
    reordered = NESTED_EXPERIENCE.replace("description: First bullet", "description: First bullet\n      position: 5")

    with DataImporter(base_model=Model, engine=engine) as importer:
        importer.load_data(reordered, Experience)

    with Session(engine) as session:
        experience = session.get(Experience, {"canonical_name": "job"})
        assert [detail.canonical_name for detail in experience.details] == ["job-second", "job-first"]


def test_skills_are_tools_unless_flagged_as_keywords(tmp_path):
    engine = _make_engine(tmp_path)

    with DataImporter(base_model=Model, engine=engine) as importer:
        importer.load_data("- name: Terraform\n- name: Infrastructure as Code\n  is_keyword: true\n", Skill)

    with Session(engine) as session:
        assert session.get(Skill, {"name": "Terraform"}).is_keyword is False
        assert session.get(Skill, {"name": "Infrastructure as Code"}).is_keyword is True
