import pytest

from resume_generator.selection import Selection, SelectionError, row_key


class Skill:
    def __init__(self, name):
        self.name = name
        self._primary_keys = {"name": name}


class ExperienceDetail:
    def __init__(self, canonical_name):
        self.canonical_name = canonical_name
        self._primary_keys = {"canonical_name": canonical_name}


def names(rows):
    return [row_key(row) for row in rows]


def selection(profile=None, config=None):
    return Selection.from_layers([("the profile", profile or {}), ("config.yml", config or {})])


def test_config_exclude_applies_when_the_profile_is_silent():
    assert selection(config={"exclude": {"Skill": ["Vim"]}}).is_excluded(Skill("Vim"))


def test_profile_include_overrides_config_exclude():
    chosen = selection(profile={"include": {"Skill": ["Vim"]}}, config={"exclude": {"Skill": ["Vim"]}})

    assert not chosen.is_excluded(Skill("Vim"))
    assert chosen.pins == {"Skill": ["Vim"]}


def test_profile_exclude_overrides_config_include():
    chosen = selection(profile={"exclude": {"Skill": ["Terraform"]}}, config={"include": {"Skill": ["Terraform"]}})

    assert chosen.is_excluded(Skill("Terraform"))
    assert chosen.pins == {}


def test_overriding_one_row_leaves_the_rest_of_the_config_list_in_place():
    chosen = selection(profile={"include": {"Skill": ["Vim"]}}, config={"exclude": {"Skill": ["Vim", "Pandoc"]}})

    assert not chosen.is_excluded(Skill("Vim"))
    assert chosen.is_excluded(Skill("Pandoc"))


def test_exclusions_are_scoped_to_their_table():
    chosen = selection(config={"exclude": {"Skill": ["shared-name"]}})

    assert chosen.is_excluded(Skill("shared-name"))
    assert not chosen.is_excluded(ExperienceDetail("shared-name"))


def test_including_and_excluding_the_same_row_in_one_layer_is_an_error():
    with pytest.raises(SelectionError, match="config.yml both includes and excludes: Skill: Vim"):
        selection(config={"include": {"Skill": ["Vim"]}, "exclude": {"Skill": ["Vim"]}})


@pytest.mark.parametrize(
    "layer, message",
    [
        ({"exclude": ["Vim"]}, "must map table names to lists of keys"),
        ({"exclude": {"Skill": "Vim"}}, "'exclude.Skill' in config.yml must be a list of keys"),
    ],
)
def test_malformed_layers_are_rejected(layer, message):
    with pytest.raises(SelectionError, match=message):
        selection(config=layer)


def test_order_puts_pins_first_in_listed_order_and_drops_exclusions():
    chosen = selection(
        profile={"include": {"Skill": ["Docker"]}},
        config={"include": {"Skill": ["Python"]}, "exclude": {"Skill": ["Vim"]}},
    )
    ranked = [Skill("Git"), Skill("Vim"), Skill("Python"), Skill("Docker"), Skill("AWS")]

    assert names(chosen.order(ranked)) == ["Docker", "Python", "Git", "AWS"]


def test_pins_for_rows_not_in_the_list_are_ignored():
    chosen = selection(profile={"include": {"Skill": ["Kubernetes"]}})

    assert names(chosen.order([Skill("Git")])) == ["Git"]


def test_unknown_references_name_the_problem_and_suggest_matches():
    chosen = selection(
        profile={"include": {"Skill": ["Terrafrom"]}},
        config={"exclude": {"Spaceship": ["x"]}},
    )

    problems = chosen.unknown_references({"Skill": {"Terraform", "Python"}, "Project": {"zenplate"}})

    assert problems == [
        "no Skill named 'Terrafrom' (did you mean: Terraform)",
        "unknown table 'Spaceship' (known tables: Project, Skill)",
    ]


def test_empty_selection_changes_nothing():
    rows = [Skill("Git"), Skill("Vim")]

    assert names(Selection().order(rows)) == ["Git", "Vim"]
    assert Selection().references() == []
