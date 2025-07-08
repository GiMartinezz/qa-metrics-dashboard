SELECT 
    severity.item AS severity_level,
    COUNT(*) AS defect_count
FROM 
    jiraraw.all_issues
CROSS JOIN UNNEST("Severity[dropdown]") AS severity(item)
WHERE 
    type = 'Defect'
    AND updated BETWEEN $__timeFrom() AND $__timeTo()
GROUP BY 
    severity.item
ORDER BY 
    defect_count DESC;