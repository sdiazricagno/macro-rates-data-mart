select curve_date
from {{ ref('fct_curve_spreads') }}
where (
        yield_2y is not null
        and yield_10y is not null
        and abs(spread_2s10s - (yield_10y - yield_2y)) > 1e-8
    )
    or (
        yield_3m is not null
        and yield_10y is not null
        and abs(spread_3m10y - (yield_10y - yield_3m)) > 1e-8
    )
    or ((yield_2y is null or yield_10y is null) and spread_2s10s is not null)
    or ((yield_3m is null or yield_10y is null) and spread_3m10y is not null)
    or is_inverted_2s10s is distinct from (
        case
            when spread_2s10s is null then null
            when spread_2s10s < 0 then true
            else false
        end
    )
    or is_inverted_3m10y is distinct from (
        case
            when spread_3m10y is null then null
            when spread_3m10y < 0 then true
            else false
        end
    )
