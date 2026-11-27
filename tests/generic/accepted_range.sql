{% test accepted_range(model, column_name, min_value, max_value) %}
select {{ column_name }} as value_out_of_range
from {{ model }}
where {{ column_name }} is not null
    and (
        {{ column_name }} < {{ min_value }}
        or {{ column_name }} > {{ max_value }}
    )
{% endtest %}
