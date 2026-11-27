-- Stress is the conjunction of a negative 2s10s spread and NFCI above zero.
-- Unemployment is carried alongside the flag and is not an input to the rule.
-- A null input leaves stress_regime null rather than treating the day as calm.
select
    cast(spreads.curve_date as date) as curve_date,
    cast(spreads.spread_2s10s as double) as spread_2s10s,
    cast(spreads.is_inverted_2s10s as boolean) as is_inverted_2s10s,
    cast(nfci.nfci as double) as nfci,
    cast(nfci.nfci_asof_date as date) as nfci_asof_date,
    cast(
        case
            when nfci.nfci is null then null
            when nfci.nfci > 0 then true
            else false
        end as boolean
    ) as nfci_above_zero,
    cast(
        case
            when spreads.spread_2s10s is null or nfci.nfci is null then null
            when spreads.spread_2s10s < 0 and nfci.nfci > 0 then true
            else false
        end as boolean
    ) as stress_regime,
    cast('2s10s_negative_and_nfci_positive' as varchar) as rule_code,
    cast(unrate.unemployment_rate as double) as unemployment_rate
from {{ ref('fct_curve_spreads') }} as spreads
inner join {{ ref('int_nfci_daily') }} as nfci
    on nfci.calendar_date = spreads.curve_date
inner join {{ ref('int_unrate_daily') }} as unrate
    on unrate.calendar_date = spreads.curve_date
