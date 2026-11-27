with bounds as (
    select
        (
            select min(observation_date)
            from {{ ref('stg_fred__dgs10') }}
            where measure_value is not null
        ) as start_date,
        (
            select max(observation_date) as end_date
            from (
                select max(observation_date) as observation_date
                from {{ ref('stg_fred__dgs3mo') }}
                union all
                select max(observation_date) from {{ ref('stg_fred__dgs2') }}
                union all
                select max(observation_date) from {{ ref('stg_fred__dgs5') }}
                union all
                select max(observation_date) from {{ ref('stg_fred__dgs10') }}
                union all
                select max(observation_date) from {{ ref('stg_fred__dgs30') }}
                union all
                select max(observation_date) from {{ ref('stg_fred__dff') }}
            ) as series_ends
        ) as end_date
),

spine as (
    select cast(series.generated as date) as calendar_date
    from generate_series(
        (select start_date from bounds),
        (select end_date from bounds),
        interval 1 day
    ) as series(generated)
),

closures as (
    select cast(holiday_date as date) as closure_date
    from {{ ref('us_market_holidays') }}
    union
    select cast(closure_date as date) as closure_date
    from {{ ref('us_market_extra_closures') }}
)

select spine.calendar_date
from spine
left join closures
    on closures.closure_date = spine.calendar_date
where extract(isodow from spine.calendar_date) between 1 and 5
    and closures.closure_date is null
