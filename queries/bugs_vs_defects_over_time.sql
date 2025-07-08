SELECT 
    updated AS done_date,
    COUNT(key) AS issue_count,
    ARRAY_AGG(key) AS issue_keys
FROM jiraraw.my_bd
WHERE 
    status = 'Done'
    AND type IN ('Defect', 'Story', 'Story Bug')
    AND updated BETWEEN FROM_UNIXTIME(${__from} / 1000) AND FROM_UNIXTIME(${__to} / 1000)
GROUP BY updated
ORDER BY updated ASC;