with filled as (
    {{ forward_filled_series(ref('stg_fred__nfci'), var('max_fill_weekly_business_days')) }}
)

select
    cast(filled.calendar_date as date) as calendar_date,
    cast(filled.filled_value as double) as nfci,
    cast(filled.asof_date as date) as nfci_asof_date,
    cast(filled.business_days_carried as integer) as nfci_days_carried
from filled
