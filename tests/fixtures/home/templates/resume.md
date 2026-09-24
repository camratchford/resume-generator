{% set candidate = Candidate[0] %}
# {{ candidate.name | upper }}

%% {{ candidate.email }} || {{ candidate.telephone | phone_num_fmt }} %%

## SKILLS

%( {{ Skill | join('||') }} )%

## WORK EXPERIENCE

{% for exp in Experience %}
{% if exp.is_career_gap %}
### {{ exp.title }}
{% else %}
### {{ exp.title }} at {{ exp.company }}
{% endif %}

{{ exp.description }}

%( {{ exp.skills | join('||') }} )%
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
