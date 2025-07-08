WITH StatusDates AS (
    SELECT
        id,
        type,
        MIN(CASE WHEN b."to" = 'In Progress' THEN from_iso8601_timestamp(b.date) END) as StartDate,
        MAX(CASE WHEN b."to" = 'Done' THEN from_iso8601_timestamp(b.date) END) as DoneDate
    FROM jiraraw.all_issues a
    CROSS JOIN UNNEST(a.status_changes) as t (b)
    GROUP BY a.id, a.type
)
SELECT
  AVG(CASE WHEN type = 'Defect' THEN date_diff('day', StartDate, DoneDate) ELSE NULL END) AS average_process_days_defect,
  AVG(CASE WHEN type = 'Story' THEN date_diff('day', StartDate, DoneDate) ELSE NULL END) AS average_process_days_story,
  AVG(CASE WHEN type = 'Story Bug' THEN date_diff('day', StartDate, DoneDate) ELSE NULL END) AS average_process_days_story_bug
FROM StatusDates
WHERE StartDate IS NOT NULL AND DoneDate IS NOT NULL
  AND DoneDate BETWEEN $__timeFrom() AND $__timeTo();