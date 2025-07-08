SELECT 
    d.key AS defect_key, 
    COUNT(sb.id) AS story_bug_count
FROM 
    jiraraw.all_issues AS d
LEFT JOIN 
    jiraraw.all_issues AS sb ON d.key = sb.parent_id AND sb.type = 'Story Bug' AND sb.id != '4392'
WHERE 
    d.type = 'Defect'
    AND $__timeFilter(d.updated)
GROUP BY 
    d.key;