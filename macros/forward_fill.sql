{% macro forward_filled_series(staging_relation, max_days) %}
    -- Last observation carried forward onto the business-day calendar.
    -- No backfill. A print dated on a weekend or holiday becomes visible on
    -- the next business day. business_days_carried is the number of business
    -- days strictly after the print. Values past max_days stay null.
    with calendar as (
        select
            calendar_date,
            cast(row_number() over (order by calendar_date) as integer) as biz_index
        from {{ ref('int_business_calendar') }}
    ),
    observed as (
        select
            observation_date,
            measure_value
        from {{ staging_relation }}
        where measure_value is not null
    ),
    spine as (
        select calendar_date as spine_date
        from calendar
        union
        select observation_date as spine_date
        from observed
    ),
    placed as (
        select
            spine.spine_date,
            observed.measure_value,
            calendar.biz_index
        from spine
        left join observed
            on observed.observation_date = spine.spine_date
        left join calendar
            on calendar.calendar_date = spine.spine_date
    ),
    marked as (
        select
            spine_date,
            measure_value,
            max(case when measure_value is not null then spine_date end) over (
                order by spine_date
                rows between unbounded preceding and current row
            ) as asof_date,
            max(biz_index) over (
                order by spine_date
                rows between unbounded preceding and current row
            ) as anchor_index
        from placed
    ),
    measured as (
        select
            calendar.calendar_date,
            source.measure_value,
            marked.asof_date,
            case
                when marked.asof_date is null then null
                when anchor.anchor_index is null then calendar.biz_index
                else calendar.biz_index - anchor.anchor_index
            end as raw_days_carried
        from calendar
        inner join marked
            on marked.spine_date = calendar.calendar_date
        left join observed as source
            on source.observation_date = marked.asof_date
        left join marked as anchor
            on anchor.spine_date = marked.asof_date
    )
    select
        cast(calendar_date as date) as calendar_date,
        case
            when raw_days_carried is not null and raw_days_carried <= {{ max_days }}
                then cast(measure_value as double)
        end as filled_value,
        case
            when raw_days_carried is not null and raw_days_carried <= {{ max_days }}
                then cast(asof_date as date)
        end as asof_date,
        case
            when raw_days_carried is not null and raw_days_carried <= {{ max_days }}
                then cast(raw_days_carried as integer)
        end as business_days_carried
    from measured
{% endmacro %}
