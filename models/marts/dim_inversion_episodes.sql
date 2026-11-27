with long_spreads as (
    select
        curve_date,
        '2s10s' as spread_code,
        spread_2s10s as spread_pp
    from {{ ref('fct_curve_spreads') }}
    where spread_2s10s is not null
    union all
    select
        curve_date,
        '3m10y' as spread_code,
        spread_3m10y as spread_pp
    from {{ ref('fct_curve_spreads') }}
    where spread_3m10y is not null
),

marked as (
    select
        curve_date,
        spread_code,
        spread_pp,
        spread_pp < 0 as is_inverted,
        case when spread_pp < 0 then 0 else 1 end as breaker
    from long_spreads
),

grouped as (
    select
        curve_date,
        spread_code,
        spread_pp,
        is_inverted,
        sum(breaker) over (
            partition by spread_code
            order by curve_date
            rows between unbounded preceding and current row
        ) as episode_group
    from marked
),

closed as (
    select
        spread_code,
        episode_group,
        min(curve_date) as start_date,
        max(curve_date) as end_date,
        cast(count(*) as integer) as length_business_days,
        min(spread_pp) as trough_spread_pp
    from grouped
    where is_inverted
    group by spread_code, episode_group
),

troughs as (
    select
        grouped.spread_code,
        grouped.episode_group,
        min(grouped.curve_date) as trough_date
    from grouped
    inner join closed
        on closed.spread_code = grouped.spread_code
        and closed.episode_group = grouped.episode_group
        and grouped.spread_pp = closed.trough_spread_pp
    where grouped.is_inverted
    group by grouped.spread_code, grouped.episode_group
),

last_print as (
    select
        spread_code,
        max(curve_date) as last_date
    from long_spreads
    group by spread_code
)

select
    cast(closed.spread_code || '_' || cast(closed.start_date as varchar) as varchar) as episode_id,
    cast(closed.spread_code as varchar) as spread_code,
    cast(closed.start_date as date) as start_date,
    cast(closed.end_date as date) as end_date,
    closed.length_business_days,
    cast(closed.end_date - closed.start_date + 1 as integer) as length_calendar_days,
    cast(closed.trough_spread_pp as double) as trough_spread_pp,
    cast(round(-100.0 * closed.trough_spread_pp, 1) as double) as depth_bps,
    cast(troughs.trough_date as date) as trough_date,
    cast(closed.end_date = last_print.last_date as boolean) as is_open
from closed
inner join troughs
    on troughs.spread_code = closed.spread_code
    and troughs.episode_group = closed.episode_group
inner join last_print
    on last_print.spread_code = closed.spread_code
