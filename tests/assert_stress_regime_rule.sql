select curve_date
from {{ ref('fct_stress_regime') }}
where rule_code <> '2s10s_negative_and_nfci_positive'
    or nfci_above_zero is distinct from (
        case
            when nfci is null then null
            when nfci > 0 then true
            else false
        end
    )
    or stress_regime is distinct from (
        case
            when spread_2s10s is null or nfci is null then null
            when spread_2s10s < 0 and nfci > 0 then true
            else false
        end
    )
