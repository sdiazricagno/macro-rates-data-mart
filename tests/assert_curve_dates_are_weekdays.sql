select curve_date
from {{ ref('fct_yield_curve_daily') }}
where extract(isodow from curve_date) in (6, 7)
