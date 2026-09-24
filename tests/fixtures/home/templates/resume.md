{% set candidate = Candidate[0] %}
# {{ candidate.name | upper }}

%% {{ candidate.email }} || {{ candidate.telephone | phone_num_fmt }} %%

## SKILLS

%( {{ Skill | rank_skills | join('||') }} )%

## WORK EXPERIENCE

{% for exp in Experience %}
{% if exp.is_career_gap %}
### {{ exp.title }}
{% else %}
### {{ exp.title }} at {{ exp.company }}
{% endif %}

{% for detail in exp.details | rank_details -%}
- {{ detail.description }}
{% endfor %}

%( {{ exp.skills | rank_skills | join('||') }} )%
{% endfor %}

## PROJECTS

{% for proj in Project %}
### {{ proj.name }}

{{ proj.description }}
{% endfor %}

## EDUCATION

{% for edu in Education %}
### {{ edu.institution }}
{% endfor %}

## HOBBIES

{% for hobby in Hobby %}
### {{ hobby.name }}
{% endfor %}
