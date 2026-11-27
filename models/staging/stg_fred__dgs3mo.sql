select
    cast(observation_date as date) as observation_date,
    'DGS3MO' as series_id,
    'yield_3m' as measure_name,
    cast(value as double) as measure_value,
    'percent' as unit,
    'daily' as frequency,
    'not seasonally adjusted' as seasonal_adjustment
from {{ source('fred', 'dgs3mo') }}
