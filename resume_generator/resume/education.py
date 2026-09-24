from datetime import date
from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship

from resume_generator.resume.model import Model

if TYPE_CHECKING:
    from resume_generator.resume.candidate import Candidate
    from resume_generator.resume.project import Project
    from resume_generator.resume.skill import Skill


class EducationSkills(Model, table=True):
    __tablename__ = "education_skills"
    skill_name: str = Field(default=None, foreign_key="skill.name", primary_key=True)
    education_canonical_name: str = Field(default=None, foreign_key="education.canonical_name", primary_key=True)


class Education(Model, table=True):
    __tablename__ = "education"
    canonical_name: str = Field(default=None, primary_key=True)
    institution: str = Field(default=None)
    location: str = Field(default=None)
    received: str = Field(default=None)
    date_from: date = Field(default=None)
    date_to: date = Field(default=None)
    candidate_name: str = Field(default=None, foreign_key="candidate.name")
    candidate: "Candidate" = Relationship(back_populates="educations")
    skills: list["Skill"] = Relationship(back_populates="educations", link_model=EducationSkills)
    projects: list["Project"] = Relationship(back_populates="education")
