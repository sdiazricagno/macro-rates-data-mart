with panel as (
    select
        min(calendar_date) as start_date,
        max(calendar_date) as end_date
    from {{ ref('int_business_calendar') }}
),

coverage as (
    select
        min(holiday_date) as first_holiday,
        max(holiday_date) as last_holiday
    from {{ ref('us_market_holidays') }}
)

select
    panel.start_date,
    panel.end_date,
    coverage.first_holiday,
    coverage.last_holiday
from panel
cross join coverage
where panel.start_date < coverage.first_holiday
    or panel.end_date > coverage.last_holiday
