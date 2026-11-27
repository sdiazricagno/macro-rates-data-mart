select
    cast(curve.curve_date as date) as curve_date,
    cast(curve.yield_2y as double) as yield_2y,
    cast(curve.yield_10y as double) as yield_10y,
    cast(curve.fed_funds_effective as double) as fed_funds_effective,
    cast(cpi.cpi_index as double) as cpi_index,
    cast(cpi.cpi_yoy_pct as double) as cpi_yoy_pct,
    cast(cpi.cpi_asof_date as date) as cpi_asof_date,
    cast(
        case
            when curve.yield_2y is null or cpi.cpi_yoy_pct is null then null
            else curve.yield_2y - cpi.cpi_yoy_pct
        end as double
    ) as real_yield_2y,
    cast(
        case
            when curve.yield_10y is null or cpi.cpi_yoy_pct is null then null
            else curve.yield_10y - cpi.cpi_yoy_pct
        end as double
    ) as real_yield_10y,
    cast(
        case
            when curve.fed_funds_effective is null or cpi.cpi_yoy_pct is null then null
            else curve.fed_funds_effective - cpi.cpi_yoy_pct
        end as double
    ) as real_fed_funds
from {{ ref('fct_yield_curve_daily') }} as curve
inner join {{ ref('int_cpi_daily') }} as cpi
    on cpi.calendar_date = curve.curve_date
