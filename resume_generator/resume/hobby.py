from datetime import date
from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship

from resume_generator.resume.model import Model

if TYPE_CHECKING:
    from resume_generator.resume.candidate import Candidate
    from resume_generator.resume.project import Project
    from resume_generator.resume.skill import Skill


class HobbySkills(Model, table=True):
    __tablename__ = "hobby_skills"
    skill_name: str = Field(default=None, foreign_key="skill.name", primary_key=True)
    hobby_id: str = Field(default=None, foreign_key="hobby.canonical_name", primary_key=True)


class Hobby(Model, table=True):
    canonical_name: str = Field(default=None, primary_key=True)
    name: str = Field(default=None)
    description: str = Field(default=None)
    date_from: date = Field(default=None)
    date_to: date = Field(default=None, nullable=True)
    candidate_name: str = Field(default=None, foreign_key="candidate.name")
    candidate: "Candidate" = Relationship(back_populates="hobbies")
    skills: list["Skill"] = Relationship(back_populates="hobbies", link_model=HobbySkills)

    projects: list["Project"] = Relationship(back_populates="hobby")
