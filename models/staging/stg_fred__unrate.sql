select
    cast(observation_date as date) as observation_date,
    'UNRATE' as series_id,
    'unemployment_rate' as measure_name,
    cast(value as double) as measure_value,
    'percent' as unit,
    'monthly' as frequency,
    'seasonally adjusted' as seasonal_adjustment
from {{ source('fred', 'unrate') }}
