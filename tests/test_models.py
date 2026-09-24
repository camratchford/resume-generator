from resume_generator.resume import Candidate, Skill


def test_candidate_urls_are_built_from_usernames():
    candidate = Candidate(name="Test", github_user="octocat", linkedin_user="test-user")

    assert candidate.github_url == "https://github.com/octocat"
    assert candidate.linkedin_url == "https://www.linkedin.com/in/test-user"


def test_candidate_urls_are_empty_without_usernames():
    candidate = Candidate(name="Test")

    assert candidate.github_url == ""
    assert candidate.linkedin_url == ""


def test_candidate_skills_are_collected_from_every_section_without_duplicates(accessor):
    candidate = accessor["Candidate"][0]

    assert sorted(skill.name for skill in candidate.skills) == ["Python", "Terraform"]


def test_candidate_back_populates_its_sections(accessor):
    candidate = accessor["Candidate"][0]

    assert {experience.canonical_name for experience in candidate.experience} == {
        "test-co-engineer",
        "test-career-gap",
    }
    assert [education.canonical_name for education in candidate.educations] == ["test-university"]
    assert [hobby.canonical_name for hobby in candidate.hobbies] == ["tinkering"]
    assert {project.canonical_name for project in candidate.projects} == {"test-project", "hobby-project"}


def test_skill_back_populates_where_it_was_used(accessor):
    python = accessor.get_by_pk("Skill", name="Python")

    assert {experience.canonical_name for experience in python.experiences} == {"test-co-engineer", "test-career-gap"}
    assert [education.canonical_name for education in python.educations] == ["test-university"]
    assert [hobby.canonical_name for hobby in python.hobbies] == ["tinkering"]


def test_skill_renders_as_its_name():
    assert str(Skill(name="Python")) == "Python"


def test_experience_skills_are_collected_from_its_details_without_duplicates(accessor):
    experience = accessor.get_by_pk("Experience", canonical_name="test-co-engineer")

    assert [skill.name for skill in experience.skills] == ["Python", "Terraform"]


def test_experience_description_lists_each_detail_as_a_bullet(accessor):
    experience = accessor.get_by_pk("Experience", canonical_name="test-co-engineer")

    assert experience.description == "- Did testing things.\n- Automated test infrastructure.\n"


def test_detail_links_back_to_its_experience(accessor):
    detail = accessor.get_by_pk("ExperienceDetail", canonical_name="test-co-infrastructure")

    assert detail.experience.canonical_name == "test-co-engineer"
    assert detail.experience_canonical_name == "test-co-engineer"


def test_model_repr_and_hash_use_primary_keys():
    first = Candidate(name="Test")
    second = Candidate(name="Test")

    assert repr(first) == "Candidate(name=Test)"
    assert hash(first) == hash(second)


def test_career_gap_is_flagged_and_has_no_company(accessor):
    career_gap = accessor.get_by_pk("Experience", canonical_name="test-career-gap")
    job = accessor.get_by_pk("Experience", canonical_name="test-co-engineer")

    assert career_gap.is_career_gap is True
    assert career_gap.company is None
    assert job.is_career_gap is False


def test_skill_usage_count_spans_every_section(accessor):
    python = accessor.get_by_pk("Skill", name="Python")
    terraform = accessor.get_by_pk("Skill", name="Terraform")

    assert python.usage_count == 7
    assert terraform.usage_count == 1
