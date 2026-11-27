with filled as (
    {{ forward_filled_series(ref('stg_fred__unrate'), var('max_fill_monthly_business_days')) }}
)

select
    cast(filled.calendar_date as date) as calendar_date,
    cast(filled.filled_value as double) as unemployment_rate,
    cast(filled.asof_date as date) as unemployment_asof_date,
    cast(filled.business_days_carried as integer) as unemployment_days_carried
from filled
