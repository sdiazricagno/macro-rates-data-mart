select
    cast(observation_date as date) as observation_date,
    'DFF' as series_id,
    'fed_funds_effective' as measure_name,
    cast(value as double) as measure_value,
    'percent' as unit,
    'daily' as frequency,
    'not seasonally adjusted' as seasonal_adjustment
from {{ source('fred', 'dff') }}
