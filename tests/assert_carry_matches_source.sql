with checked as (
    select
        yields.curve_date,
        'yield_10y' as series_name,
        yields.yield_10y as filled_value,
        yields.yield_10y_asof_date as asof_date,
        yields.yield_10y_days_carried as days_carried,
        source.measure_value as source_value
    from {{ ref('int_yields_daily') }} as yields
    left join {{ ref('stg_fred__dgs10') }} as source
        on source.observation_date = yields.yield_10y_asof_date

    union all

    select
        yields.curve_date,
        'yield_2y',
        yields.yield_2y,
        yields.yield_2y_asof_date,
        yields.yield_2y_days_carried,
        source.measure_value
    from {{ ref('int_yields_daily') }} as yields
    left join {{ ref('stg_fred__dgs2') }} as source
        on source.observation_date = yields.yield_2y_asof_date

    union all

    select
        yields.curve_date,
        'yield_30y',
        yields.yield_30y,
        yields.yield_30y_asof_date,
        yields.yield_30y_days_carried,
        source.measure_value
    from {{ ref('int_yields_daily') }} as yields
    left join {{ ref('stg_fred__dgs30') }} as source
        on source.observation_date = yields.yield_30y_asof_date
),

calendar as (
    select
        calendar_date,
        cast(row_number() over (order by calendar_date) as integer) as biz_index
    from {{ ref('int_business_calendar') }}
)

select
    checked.curve_date,
    checked.series_name
from checked
inner join calendar
    on calendar.calendar_date = checked.curve_date
where checked.filled_value is not null
    and (
        abs(checked.filled_value - checked.source_value) > 1e-8
        or checked.asof_date > checked.curve_date
        or (checked.days_carried = 0 and checked.asof_date <> checked.curve_date)
        or (checked.days_carried > 0 and checked.asof_date >= checked.curve_date)
        or checked.days_carried is distinct from (
            select cast(count(*) as integer)
            from calendar as prior
            where prior.calendar_date > checked.asof_date
                and prior.calendar_date <= checked.curve_date
        )
    )
