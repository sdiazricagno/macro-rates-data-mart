with
{% set series = [
    ("yield_3m", "stg_fred__dgs3mo"),
    ("yield_2y", "stg_fred__dgs2"),
    ("yield_5y", "stg_fred__dgs5"),
    ("yield_10y", "stg_fred__dgs10"),
    ("yield_30y", "stg_fred__dgs30"),
    ("fed_funds_effective", "stg_fred__dff"),
] %}
{% for alias, model_name in series %}
{{ alias }} as (
    {{ forward_filled_series(ref(model_name), var("max_fill_daily_business_days")) }}
),
{% endfor %}
calendar as (
    select calendar_date
    from {{ ref("int_business_calendar") }}
)

select
    cast(calendar.calendar_date as date) as curve_date,
    {% for alias, model_name in series %}
    cast({{ alias }}.filled_value as double) as {{ alias }},
    cast({{ alias }}.asof_date as date) as {{ alias }}_asof_date,
    cast({{ alias }}.business_days_carried as integer) as {{ alias }}_days_carried
    {%- if not loop.last %},{% endif %}
    {% endfor %}
from calendar
{% for alias, model_name in series %}
left join {{ alias }}
    on {{ alias }}.calendar_date = calendar.calendar_date
{% endfor %}
