select
    cast(observation_date as date) as observation_date,
    'DGS2' as series_id,
    'yield_2y' as measure_name,
    cast(value as double) as measure_value,
    'percent' as unit,
    'daily' as frequency,
    'not seasonally adjusted' as seasonal_adjustment
from {{ source('fred', 'dgs2') }}
