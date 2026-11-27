with monthly as (
    select
        observation_date,
        measure_value as cpi_index
    from {{ ref('stg_fred__cpiaucsl') }}
    where measure_value is not null
)

select
    current_month.observation_date,
    current_month.cpi_index as measure_value,
    current_month.cpi_index,
    case
        when prior_month.cpi_index is not null and prior_month.cpi_index <> 0
            then (current_month.cpi_index / prior_month.cpi_index - 1.0) * 100.0
    end as cpi_yoy_pct
from monthly as current_month
left join monthly as prior_month
    on prior_month.observation_date = current_month.observation_date - interval 12 month
