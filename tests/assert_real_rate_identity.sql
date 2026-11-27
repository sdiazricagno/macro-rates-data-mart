select curve_date
from {{ ref('fct_real_rates') }}
where (
        yield_10y is not null
        and cpi_yoy_pct is not null
        and abs(real_yield_10y - (yield_10y - cpi_yoy_pct)) > 1e-8
    )
    or (
        yield_2y is not null
        and cpi_yoy_pct is not null
        and abs(real_yield_2y - (yield_2y - cpi_yoy_pct)) > 1e-8
    )
    or (
        fed_funds_effective is not null
        and cpi_yoy_pct is not null
        and abs(real_fed_funds - (fed_funds_effective - cpi_yoy_pct)) > 1e-8
    )
    or ((yield_10y is null or cpi_yoy_pct is null) and real_yield_10y is not null)
    or ((yield_2y is null or cpi_yoy_pct is null) and real_yield_2y is not null)
    or (
        (fed_funds_effective is null or cpi_yoy_pct is null)
        and real_fed_funds is not null
    )
