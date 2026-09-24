from .candidate import Candidate
from .education import Education
from .experience import Experience, ExperienceDetail
from .hobby import Hobby
from .model import Model
from .project import Project, ProjectCategory
from .skill import Skill, SkillCategory

ALL_MODELS = (
    SkillCategory,
    Skill,
    Candidate,
    Education,
    Hobby,
    Experience,
    ProjectCategory,
    Project,
)

__all__ = [
    "Model",
    "SkillCategory",
    "Skill",
    "Candidate",
    "Education",
    "ProjectCategory",
    "Project",
    "Hobby",
    "Experience",
    "ExperienceDetail",
    "ALL_MODELS",
]
