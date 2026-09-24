from types import SimpleNamespace

import pytest
from jinja2 import Environment

from resume_generator.ranking import CategoryRanker, PositionRanker, load_profile


def make_skill(name, *category_names):
    return SimpleNamespace(name=name, categories=[SimpleNamespace(name=category) for category in category_names])


def make_detail(name, position, *skills):
    return SimpleNamespace(name=name, position=position, skills=list(skills))


PYTHON = make_skill("Python", "Programming", "DevOps")
TERRAFORM = make_skill("Terraform", "IaC", "DevOps")
DNS = make_skill("DNS", "Networking")
ZIGBEE = make_skill("ZigBee", "IoT", "Networking")
VIM = make_skill("Vim", "Development Tools")


def names(items):
    return [item.name for item in items]


def test_position_ranker_sorts_by_position():
    details = [make_detail("second", 1), make_detail("first", 0), make_detail("third", 2)]

    assert names(PositionRanker().rank_details(details)) == ["first", "second", "third"]


def test_position_ranker_puts_unpositioned_details_last():
    details = [make_detail("unpositioned", None), make_detail("first", 0)]

    assert names(PositionRanker().rank_details(details)) == ["first", "unpositioned"]


def test_position_ranker_applies_details_limit():
    details = [make_detail(str(position), position) for position in range(5)]

    assert names(PositionRanker(details_limit=2).rank_details(details)) == ["0", "1"]


def test_position_ranker_keeps_skill_order():
    assert names(PositionRanker().rank_skills([VIM, PYTHON, DNS])) == ["Vim", "Python", "DNS"]


def test_category_ranker_puts_best_category_first():
    details = [make_detail("infrastructure", 0, TERRAFORM), make_detail("network", 1, DNS)]

    assert names(CategoryRanker(["Networking", "IaC"]).rank_details(details)) == ["network", "infrastructure"]


def test_category_ranker_breaks_ties_by_number_of_matching_skills():
    details = [make_detail("one-match", 0, DNS), make_detail("two-matches", 1, DNS, ZIGBEE)]

    assert names(CategoryRanker(["Networking"]).rank_details(details)) == ["two-matches", "one-match"]


def test_category_ranker_prefers_rank_over_match_count():
    details = [make_detail("many-weaker", 0, PYTHON, TERRAFORM), make_detail("one-stronger", 1, DNS)]

    assert names(CategoryRanker(["Networking", "DevOps"]).rank_details(details)) == ["one-stronger", "many-weaker"]


def test_category_ranker_falls_back_to_position():
    details = [make_detail("later", 3, DNS), make_detail("earlier", 1, DNS)]

    assert names(CategoryRanker(["Networking"]).rank_details(details)) == ["earlier", "later"]


def test_category_ranker_puts_unmatched_details_last_in_position_order():
    details = [make_detail("editor", 0, VIM), make_detail("no-skills", 1), make_detail("network", 2, DNS)]

    assert names(CategoryRanker(["Networking"]).rank_details(details)) == ["network", "editor", "no-skills"]


def test_category_ranker_applies_details_limit():
    details = [make_detail("editor", 0, VIM), make_detail("network", 1, DNS), make_detail("iot", 2, ZIGBEE)]

    assert names(CategoryRanker(["IoT", "Networking"], details_limit=2).rank_details(details)) == ["iot", "network"]


def test_category_ranker_orders_skills_by_best_category_and_keeps_ties_stable():
    skills = [VIM, PYTHON, DNS, ZIGBEE, TERRAFORM]

    ranked = CategoryRanker(["Networking", "DevOps"]).rank_skills(skills)

    assert names(ranked) == ["DNS", "ZigBee", "Python", "Terraform", "Vim"]


def test_load_profile_reads_categories_and_limit(tmp_path):
    (tmp_path / "field.yml").write_text("categories:\n- Networking\n- IoT\nbullets_per_job: 3\n")

    assert load_profile(tmp_path, "field") == {"categories": ["Networking", "IoT"], "bullets_per_job": 3}


def test_load_profile_lists_available_profiles_when_missing(tmp_path):
    (tmp_path / "devops.yml").write_text("categories: []\n")

    with pytest.raises(FileNotFoundError, match="Available profiles: devops"):
        load_profile(tmp_path, "field")


def test_load_profile_rejects_non_list_categories(tmp_path):
    (tmp_path / "broken.yml").write_text("categories: Networking\n")

    with pytest.raises(TypeError, match="sequence"):
        load_profile(tmp_path, "broken")


def test_position_ranker_applies_skills_limit():
    assert names(PositionRanker(skills_limit=2).rank_skills([VIM, PYTHON, DNS])) == ["Vim", "Python"]


def test_category_ranker_applies_skills_limit_after_ranking():
    ranked = CategoryRanker(["Networking"], skills_limit=2).rank_skills([VIM, PYTHON, DNS, ZIGBEE])

    assert names(ranked) == ["DNS", "ZigBee"]


def test_explicit_limit_overrides_the_ranker_default():
    ranker = CategoryRanker(["Networking"], details_limit=1, skills_limit=1)
    details = [make_detail("network", 0, DNS), make_detail("iot", 1, ZIGBEE)]

    assert names(ranker.rank_details(details, limit=2)) == ["network", "iot"]
    assert names(ranker.rank_skills([VIM, DNS, ZIGBEE], limit=3)) == ["DNS", "ZigBee", "Vim"]


def test_limit_filters_work_from_a_template():
    environment = Environment()
    ranker = CategoryRanker(["Networking"], skills_limit=1)
    environment.filters.update(rank_skills=ranker.rank_skills)

    template = environment.from_string(
        "{{ skills | rank_skills | map(attribute='name') | join(',') }}/"
        "{{ skills | rank_skills(limit=2) | map(attribute='name') | join(',') }}"
    )

    assert template.render(skills=[VIM, DNS, ZIGBEE]) == "DNS/DNS,ZigBee"
