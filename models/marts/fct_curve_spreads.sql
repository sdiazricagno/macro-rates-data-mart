select
    cast(curve_date as date) as curve_date,
    cast(yield_3m as double) as yield_3m,
    cast(yield_2y as double) as yield_2y,
    cast(yield_10y as double) as yield_10y,
    cast(
        case
            when yield_10y is null or yield_2y is null then null
            else yield_10y - yield_2y
        end as double
    ) as spread_2s10s,
    cast(
        case
            when yield_10y is null or yield_3m is null then null
            else yield_10y - yield_3m
        end as double
    ) as spread_3m10y,
    cast(
        case
            when yield_10y is null or yield_2y is null then null
            when yield_10y - yield_2y < 0 then true
            else false
        end as boolean
    ) as is_inverted_2s10s,
    cast(
        case
            when yield_10y is null or yield_3m is null then null
            when yield_10y - yield_3m < 0 then true
            else false
        end as boolean
    ) as is_inverted_3m10y
from {{ ref('fct_yield_curve_daily') }}
