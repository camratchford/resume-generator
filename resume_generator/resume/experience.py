from datetime import date
from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship

from resume_generator.resume.model import Model

if TYPE_CHECKING:
    from resume_generator.resume.candidate import Candidate
    from resume_generator.resume.project import Project
    from resume_generator.resume.skill import Skill


class ExperienceDetailSkills(Model, table=True):
    __tablename__ = "experience_detail_skills"
    skill_name: str = Field(default=None, foreign_key="skill.name", primary_key=True)
    experience_detail_canonical_name: str = Field(
        default=None, foreign_key="experience_detail.canonical_name", primary_key=True
    )


class ExperienceDetail(Model, table=True):
    __tablename__ = "experience_detail"
    canonical_name: str = Field(default=None, primary_key=True)
    description: str = Field(nullable=False)
    position: int = Field(default=None, nullable=True)
    experience_canonical_name: str = Field(foreign_key="experience.canonical_name")
    experience: "Experience" = Relationship(back_populates="details")
    skills: list["Skill"] = Relationship(back_populates="experience_details", link_model=ExperienceDetailSkills)


class Experience(Model, table=True):
    """Work experience. Full-time employment, contract gig, volunteering, internship, etc."""

    __tablename__ = "experience"
    canonical_name: str = Field(default=None, primary_key=True)
    company: str = Field(default=None, nullable=True)
    title: str = Field(default=None)
    is_career_gap: bool = Field(default=False)
    team: str = Field(default=None, nullable=True)
    href: str = Field(default="", nullable=True)
    date_from: date = Field(default=None)
    date_to: date = Field(default=None, nullable=True)
    location: str = Field(default=None)
    candidate_name: str = Field(default=None, foreign_key="candidate.name")
    candidate: "Candidate" = Relationship(back_populates="experience")
    details: list[ExperienceDetail] = Relationship(
        back_populates="experience", sa_relationship_kwargs={"order_by": "ExperienceDetail.position"}
    )

    projects: list["Project"] = Relationship(back_populates="experience")

    @property
    def skills(self):
        return list({skill.name: skill for detail in self.details for skill in detail.skills}.values())

    @property
    def description(self):
        return "".join(f"- {detail.description}\n" for detail in self.details)
