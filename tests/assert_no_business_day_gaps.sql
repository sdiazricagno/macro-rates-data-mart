with calendar as (
    select calendar_date
    from {{ ref('int_business_calendar') }}
),

fact as (
    select curve_date
    from {{ ref('fct_yield_curve_daily') }}
)

select calendar.calendar_date as curve_date
from calendar
left join fact
    on fact.curve_date = calendar.calendar_date
where fact.curve_date is null

union all

select fact.curve_date
from fact
left join calendar
    on calendar.calendar_date = fact.curve_date
where calendar.calendar_date is null
