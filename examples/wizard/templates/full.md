{% set candidate = Candidate[0] %}
# {{ candidate.name | upper }}

%% [%+󰇰+% {{ candidate.email }}](mailto:{{ candidate.email }}) || [%+󰏲+% {{ candidate.telephone | phone_num_fmt }}](tel:{{ candidate.telephone }}) || [%++% {{ candidate.linkedin_user }}]({{ candidate.linkedin_url }}) || [%++% {{ candidate.github_user }}]({{ candidate.github_url }}) %%

---

## SUMMARY

<p class="flex-wrap">{{ candidate.short_summary }}</p>

## SKILLS

%( {{ Skill | rank_skills(kind="tool", limit=10) | join('||') }} )%

## CORE COMPETENCIES

%( {{ Skill | rank_skills(kind="keyword", limit=8) | join('||') }} )%

## WORK EXPERIENCE

{% for exp in Experience | sort(attribute='date_from', reverse=True) %}
{% if exp.is_career_gap %}
### {{ exp.title }}
{% else %}
### {{ exp.title }} <br> [{{ exp.company }}]({{ exp.href if exp.href else "" }})
{% endif %}

> %% {{ exp.location }} || *{{ exp.date_from | month_year_fmt }} - {% if exp.date_to %}{{ exp.date_to | month_year_fmt }}{% else %}Present{% endif %}* %%

#### {{ "Goals" if exp.is_career_gap else "Duties" }}

{% for detail in exp.details | rank_details -%}
- {{ detail.description }}
{% endfor %}

#### Skills

%( {{ exp.skills | rank_skills | join('||') }} )%
{% endfor %}

## PROJECTS

{% for proj in (Project | sort(attribute='date_from', reverse=True))[:2] %}
### {{ proj.name }}

> %% {{ proj.category_name }} || *{{ proj.date_from | month_year_fmt }} - {% if proj.date_to %}{{ proj.date_to | month_year_fmt }}{% else %}Present{% endif %}* %%

{{ proj.description }}

#### Skills

%( {{ proj.skills | rank_skills | join('||') }} )%
{% endfor %}

## EDUCATION

{% for edu in Education %}
### {{ edu.institution }}
> %% {{ edu.location }} || {{ edu.received }} %%

#### Skills

%( {{ edu.skills | selected | join('||') }} )%
{% endfor %}

## HOBBIES

{% for hobby in Hobby %}
### {{ hobby.name }}

{{ hobby.description }}

#### Skills

%( {{ hobby.skills | selected | join('||') }} )%
{% endfor %}
