from typing import TYPE_CHECKING, ClassVar

from sqlalchemy.ext.associationproxy import AssociationProxy, association_proxy
from sqlmodel import Field, Relationship

from resume_generator.resume.education import Education
from resume_generator.resume.experience import Experience
from resume_generator.resume.hobby import Hobby
from resume_generator.resume.model import Model
from resume_generator.resume.project import Project

if TYPE_CHECKING:
    from resume_generator.resume.skill import Skill


class Candidate(Model, table=True):
    __tablename__ = "candidate"
    name: str = Field(default=None, primary_key=True)
    about: str = Field(default=None, nullable=True)
    short_summary: str = Field(default=None, nullable=True)
    summary: str = Field(default=None, nullable=True)
    telephone: str = Field(default=None, nullable=True)
    email: str = Field(default=None, nullable=True)
    linkedin_user: str = Field(default=None, nullable=True)
    github_user: str = Field(default=None, nullable=True)
    webpage_url: str = Field(default=None, nullable=True)
    portfolio_url: str = Field(default=None, nullable=True)

    educations: list[Education] = Relationship(back_populates="candidate")
    experience: list[Experience] = Relationship(back_populates="candidate")
    projects: list[Project] = Relationship(back_populates="candidate")
    hobbies: list[Hobby] = Relationship(back_populates="candidate")

    education_skills: ClassVar[AssociationProxy] = association_proxy("educations", "skills")
    experience_skills: ClassVar[AssociationProxy] = association_proxy("experience", "skills")
    project_skills: ClassVar[AssociationProxy] = association_proxy("projects", "skills")
    hobby_skills: ClassVar[AssociationProxy] = association_proxy("hobbies", "skills")

    @property
    def skills(self) -> list["Skill"]:
        skill_lists = (*self.education_skills, *self.experience_skills, *self.project_skills, *self.hobby_skills)
        return list({skill.name: skill for skills in skill_lists for skill in skills}.values())

    @property
    def github_url(self):
        if not self.github_user:
            return ""
        return f"https://github.com/{self.github_user}"

    @property
    def linkedin_url(self):
        if not self.linkedin_user:
            return ""
        return f"https://www.linkedin.com/in/{self.linkedin_user}"
