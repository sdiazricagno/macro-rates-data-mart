select
    cast(observation_date as date) as observation_date,
    'NFCI' as series_id,
    'nfci' as measure_name,
    cast(value as double) as measure_value,
    'index' as unit,
    'weekly' as frequency,
    'not seasonally adjusted' as seasonal_adjustment
from {{ source('fred', 'nfci') }}
