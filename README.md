# resume-generator

Render resumes from structured YAML data. Your experience, skills, projects, and education live in YAML files, a Jinja2 template turns them into Markdown, and the result is converted to HTML and a PDF with WeasyPrint. Skill categories let one data set produce resumes tailored to different roles.

## Installation

Requires Python 3.12 or newer.

```shell
python -m venv .venv
.venv/bin/pip install -e ".[development]"
```

## Usage

```shell
resume-generator render OUTPUT_PATH --home-dir ~/resume-generator -t resume.md -s resume.css
```

- `OUTPUT_PATH` ending in `.pdf` is used as the file path. Any other path is treated as a directory, and the file is named `{candidate.name} - Resume.pdf` (or `-n NAME` if given).
- `--markdown` and `--html` also write the intermediate files next to the PDF.
- `--template-path` and `--css-stylesheet-path` accept a file from anywhere, instead of a name from the home directory.
- `--dry-run` renders everything in memory without writing files.

Run `resume-generator render --help` for every option.

## Home directory

The home directory defaults to `~/resume-generator` and is set with `--home-dir`:

```
home/
├── data/        YAML data files (required)
├── templates/   Jinja2 Markdown templates (required)
├── css/         Stylesheets for the PDF (required)
├── profiles/    Ranking profiles (optional)
└── config.yml   Configuration defaults (optional)
```

### Data files

Each file in `data/` holds a list of records for one table: `candidate.yml`, `experience.yml`, `education.yml`, `project.yml`, `project_category.yml`, `hobby.yml`, `skill.yml`, and `skill_category.yml`. Records refer to each other by name, and a skill referenced anywhere is created if it doesn't exist yet.

Each experience holds its bullets as nested details, each with its own skills:

```yaml
- canonical_name: example-co-engineer
  company: Example Co
  title: Engineer
  date_from: 2020-01-01
  date_to: null
  location: Calgary, AB
  candidate_name: Your Name
  details:
    - canonical_name: example-co-pipeline
      description: Built a CI/CD pipeline for 60+ services.
      skills:
        - name: Terraform
        - name: Docker
```

Set `is_career_gap: true` on an experience to mark a career gap, which templates can render without a company.

### Templates

Templates are Jinja2 Markdown. Every table is available by its model name (`Candidate`, `Experience`, `Skill`, and so on), along with these filters:

| Filter           | Purpose                                                                          |
|------------------|----------------------------------------------------------------------------------|
| `rank_details`   | Order an experience's details by the active ranking, capped at `bullets_per_job` |
| `rank_skills`    | Order skills by the active ranking, capped at `skills_per_job`                   |
| `phone_num_fmt`  | Format an 11-digit phone number as `1-555-123-4567`                              |
| `month_year_fmt` | Format a date as `January 2024`                                                  |

Both ranking filters take an optional `limit` that overrides the configured cap, for example `Skill | rank_skills(limit=20)` for a top skills list.

The Markdown supports a few extra inline syntaxes:

| Syntax           | Renders as                      |
|------------------|---------------------------------|
| `%( a \|\| b )%` | A wrapping row of skill bubbles |
| `%% a \|\| b %%` | Side-by-side columns            |
| `%m text m%`     | Muted text                      |
| `%+glyph+%`      | A Nerd Font icon                |
| `%:pg:%`         | A page break                    |

A template variable with no value, such as `{{ target_company }}`, is prompted for in a terminal form before rendering. Add a type to prompt for something other than text: `{{ years_of_experience: int }}`.

## Ranking and profiles

By default, details and skills keep the order they have in the data files. To tailor a resume, rank them by an ordered list of skill categories: details whose skills fall in the earliest categories come first, and ties go to the detail with more matching skills, then to data file order.

Pass the categories directly:

```shell
resume-generator render out/ -t resume.md -s resume.css --categories "Networking,IoT,Linux Services"
```

Or save them as a profile in `profiles/`, and select it by name:

```yaml
# profiles/field.yml
categories:
  - Networking
  - IoT
  - Linux Services
bullets_per_job: 4
skills_per_job: 8
```

```shell
resume-generator render out/ -t resume.md -s resume.css --profile field
```

`--categories` overrides a profile's category list. Unknown category or profile names are reported with the valid options.

## Configuration

`bullets_per_job` and `skills_per_job` can also be set globally in `config.yml` or for one run with `-o key=value`. A profile's values take precedence:

```yaml
# config.yml
bullets_per_job: 5
metadata_title: Your Name - Resume
```

Any `metadata_*` value overrides the matching PDF metadata field. Use `-c PATH` to load a config file from somewhere other than the home directory.

## Development

```shell
.venv/bin/pytest
.venv/bin/isort resume_generator tests
.venv/bin/ruff check --fix
.venv/bin/ruff format
```

The tests use the sample home directory in `tests/fixtures/home`.
