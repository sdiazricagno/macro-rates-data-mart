{% test zscore_anomaly(model, column_name, order_by, threshold=6, window=252) %}
with ordered as (
    select
        {{ order_by }} as order_key,
        {{ column_name }} as metric
    from {{ model }}
    where {{ column_name }} is not null
),

scored as (
    select
        order_key,
        metric,
        avg(metric) over lookback as trailing_mean,
        stddev_samp(metric) over lookback as trailing_stddev,
        count(metric) over lookback as trailing_count
    from ordered
    window lookback as (
        order by order_key
        rows between {{ window }} preceding and 1 preceding
    )
)

select
    order_key,
    metric,
    trailing_mean,
    trailing_stddev,
    (metric - trailing_mean) / trailing_stddev as z_score
from scored
where trailing_count >= {{ window }}
    and trailing_stddev > 0
    and abs((metric - trailing_mean) / trailing_stddev) > {{ threshold }}
{% endtest %}
