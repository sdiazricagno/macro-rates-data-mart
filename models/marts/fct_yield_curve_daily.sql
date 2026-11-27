select
    cast(curve_date as date) as curve_date,
    cast(yield_3m as double) as yield_3m,
    cast(yield_2y as double) as yield_2y,
    cast(yield_5y as double) as yield_5y,
    cast(yield_10y as double) as yield_10y,
    cast(yield_30y as double) as yield_30y,
    cast(fed_funds_effective as double) as fed_funds_effective,
    cast(yield_3m_days_carried as integer) as yield_3m_days_carried,
    cast(yield_2y_days_carried as integer) as yield_2y_days_carried,
    cast(yield_5y_days_carried as integer) as yield_5y_days_carried,
    cast(yield_10y_days_carried as integer) as yield_10y_days_carried,
    cast(yield_30y_days_carried as integer) as yield_30y_days_carried,
    cast(fed_funds_effective_days_carried as integer) as fed_funds_days_carried
from {{ ref('int_yields_daily') }}
