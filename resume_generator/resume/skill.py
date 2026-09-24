from sqlmodel import Field, Relationship

from resume_generator.resume.education import Education, EducationSkills
from resume_generator.resume.experience import ExperienceDetail, ExperienceDetailSkills
from resume_generator.resume.hobby import Hobby, HobbySkills
from resume_generator.resume.model import Model
from resume_generator.resume.project import Project, ProjectSkills


class SkillCategorySkills(Model, table=True):
    __table_name__ = "skill_category_skills"
    skill_name: str = Field(default=None, foreign_key="skill.name", primary_key=True)
    category_name: str = Field(default=None, foreign_key="skill_category.name", primary_key=True)


class SkillCategory(Model, table=True):
    __tablename__ = "skill_category"
    name: str = Field(default=None, primary_key=True)
    skills: list["Skill"] = Relationship(back_populates="categories", link_model=SkillCategorySkills)

    def __str__(self):
        return f"{self.name}"

    def __repr__(self):
        return f"{self.name}"


class Skill(Model, table=True):
    name: str = Field(default=None, primary_key=True)
    experience_details: list[ExperienceDetail] = Relationship(
        back_populates="skills", link_model=ExperienceDetailSkills
    )
    educations: list[Education] = Relationship(back_populates="skills", link_model=EducationSkills)
    projects: list[Project] = Relationship(back_populates="skills", link_model=ProjectSkills)
    hobbies: list[Hobby] = Relationship(back_populates="skills", link_model=HobbySkills)
    categories: list[SkillCategory] = Relationship(back_populates="skills", link_model=SkillCategorySkills)

    @property
    def experiences(self):
        return list(
            {detail.experience.canonical_name: detail.experience for detail in self.experience_details}.values()
        )

    def __str__(self):
        return f"{self.name}"

    def __repr__(self):
        return f"{self.name}"
