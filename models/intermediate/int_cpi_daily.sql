with filled as (
    {{ forward_filled_series(ref('int_cpi_monthly'), var('max_fill_monthly_business_days')) }}
)

select
    cast(filled.calendar_date as date) as calendar_date,
    cast(monthly.cpi_index as double) as cpi_index,
    cast(monthly.cpi_yoy_pct as double) as cpi_yoy_pct,
    cast(filled.asof_date as date) as cpi_asof_date,
    cast(filled.business_days_carried as integer) as cpi_days_carried
from filled
left join {{ ref('int_cpi_monthly') }} as monthly
    on monthly.observation_date = filled.asof_date
