select
    cast(observation_date as date) as observation_date,
    'CPIAUCSL' as series_id,
    'cpi_index' as measure_name,
    cast(value as double) as measure_value,
    'index' as unit,
    'monthly' as frequency,
    'seasonally adjusted' as seasonal_adjustment
from {{ source('fred', 'cpiaucsl') }}
