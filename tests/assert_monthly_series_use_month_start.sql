select observation_date, 'CPIAUCSL' as series_id
from {{ ref('stg_fred__cpiaucsl') }}
where measure_value is not null
    and extract(day from observation_date) <> 1

union all

select observation_date, 'UNRATE' as series_id
from {{ ref('stg_fred__unrate') }}
where measure_value is not null
    and extract(day from observation_date) <> 1
