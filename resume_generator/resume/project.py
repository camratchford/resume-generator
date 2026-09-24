from datetime import date
from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship

from resume_generator.resume.model import Model

if TYPE_CHECKING:
    from resume_generator.resume.candidate import Candidate
    from resume_generator.resume.education import Education
    from resume_generator.resume.experience import Experience
    from resume_generator.resume.hobby import Hobby
    from resume_generator.resume.skill import Skill


class ProjectSkills(Model, table=True):
    __tablename__ = "project_skills"
    skill_name: str = Field(default=None, foreign_key="skill.name", primary_key=True)
    project_canonical_name: int = Field(default=None, foreign_key="project.canonical_name", primary_key=True)


class ProjectCategory(Model, table=True):
    __tablename__ = "project_category"
    name: str = Field(default=None, primary_key=True)
    projects: list["Project"] = Relationship(back_populates="category")


class Project(Model, table=True):
    canonical_name: str = Field(default=None, primary_key=True)
    name: str = Field(default=None)
    href: str = Field(default=None, nullable=True)
    description: str = Field(default=None)
    date_from: date = Field(default=None)
    date_to: date = Field(default=None, nullable=True)

    category_name: str = Field(foreign_key="project_category.name")
    category: ProjectCategory = Relationship(back_populates="projects")

    candidate_name: str = Field(default=None, foreign_key="candidate.name")
    candidate: "Candidate" = Relationship(back_populates="projects")

    education_canonical_name: str = Field(default=None, nullable=True, foreign_key="education.canonical_name")
    education: "Education" = Relationship(back_populates="projects")

    experience_canonical_name: str = Field(default=None, nullable=True, foreign_key="experience.canonical_name")
    experience: "Experience" = Relationship(back_populates="projects")

    hobby_canonical_name: str = Field(default=None, nullable=True, foreign_key="hobby.canonical_name")
    hobby: "Hobby" = Relationship(back_populates="projects")

    skills: list["Skill"] = Relationship(back_populates="projects", link_model=ProjectSkills)
