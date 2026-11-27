with inverted as (
    select
        curve_date,
        '2s10s' as spread_code,
        spread_2s10s as spread_pp
    from {{ ref('fct_curve_spreads') }}
    where spread_2s10s is not null
        and spread_2s10s < 0
    union all
    select
        curve_date,
        '3m10y' as spread_code,
        spread_3m10y as spread_pp
    from {{ ref('fct_curve_spreads') }}
    where spread_3m10y is not null
        and spread_3m10y < 0
),

coverage as (
    select
        inverted.curve_date,
        inverted.spread_code,
        inverted.spread_pp,
        episodes.episode_id,
        episodes.length_business_days,
        episodes.length_calendar_days,
        episodes.trough_spread_pp,
        episodes.depth_bps,
        episodes.trough_date,
        episodes.start_date,
        episodes.end_date,
        episodes.is_open
    from inverted
    left join {{ ref('dim_inversion_episodes') }} as episodes
        on episodes.spread_code = inverted.spread_code
        and inverted.curve_date between episodes.start_date and episodes.end_date
),

last_print as (
    select
        '2s10s' as spread_code,
        max(curve_date) as last_date
    from {{ ref('fct_curve_spreads') }}
    where spread_2s10s is not null
    union all
    select
        '3m10y' as spread_code,
        max(curve_date) as last_date
    from {{ ref('fct_curve_spreads') }}
    where spread_3m10y is not null
),

failures as (
    select curve_date, spread_code, 'missing episode' as issue
    from coverage
    where episode_id is null

    union all

    select curve_date, spread_code, 'overlapping episodes' as issue
    from coverage
    group by curve_date, spread_code
    having count(distinct episode_id) > 1

    union all

    select
        min(curve_date) as curve_date,
        spread_code,
        'length mismatch' as issue
    from coverage
    where episode_id is not null
    group by episode_id, spread_code, length_business_days
    having count(*) <> length_business_days

    union all

    select
        min(curve_date) as curve_date,
        spread_code,
        'trough mismatch' as issue
    from coverage
    where episode_id is not null
    group by
        episode_id,
        spread_code,
        trough_spread_pp,
        depth_bps,
        trough_date,
        start_date,
        end_date,
        length_calendar_days
    having abs(min(spread_pp) - trough_spread_pp) > 1e-8
        or abs(depth_bps - round(-100.0 * trough_spread_pp, 1)) > 1e-6
        or trough_date < start_date
        or trough_date > end_date
        or end_date < start_date
        or length_calendar_days <> end_date - start_date + 1

    union all

    select
        spreads.curve_date,
        episodes.spread_code,
        'non-inverted day inside episode' as issue
    from {{ ref('dim_inversion_episodes') }} as episodes
    inner join {{ ref('fct_curve_spreads') }} as spreads
        on spreads.curve_date between episodes.start_date and episodes.end_date
    where (
            episodes.spread_code = '2s10s'
            and (spreads.spread_2s10s is null or spreads.spread_2s10s >= 0)
        )
        or (
            episodes.spread_code = '3m10y'
            and (spreads.spread_3m10y is null or spreads.spread_3m10y >= 0)
        )

    union all

    select
        episodes.start_date as curve_date,
        episodes.spread_code,
        'open flag mismatch' as issue
    from {{ ref('dim_inversion_episodes') }} as episodes
    inner join last_print
        on last_print.spread_code = episodes.spread_code
    where episodes.is_open is distinct from (episodes.end_date = last_print.last_date)
)

select curve_date, spread_code, issue
from failures
