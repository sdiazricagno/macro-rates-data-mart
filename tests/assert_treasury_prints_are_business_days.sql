select observation_date
from {{ ref('stg_fred__dgs10') }} as prints
left join {{ ref('int_business_calendar') }} as calendar
    on calendar.calendar_date = prints.observation_date
where prints.measure_value is not null
    and extract(isodow from prints.observation_date) between 1 and 5
    and calendar.calendar_date is null
    and prints.observation_date >= (select min(calendar_date) from {{ ref('int_business_calendar') }})
    and prints.observation_date <= (select max(calendar_date) from {{ ref('int_business_calendar') }})
