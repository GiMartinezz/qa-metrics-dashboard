WITH QA_Metrics AS (
  SELECT 
    COUNT(CASE WHEN type = 'Defect' THEN 1 END) AS TotalBugsDefects,
    COUNT(CASE WHEN type = 'Story Bug' THEN 1 END) AS TotalStoryBugs
  FROM jiraraw.all_issues
  WHERE updated BETWEEN $__timeFrom() AND $__timeTo()
)
SELECT 
  TotalBugsDefects,
  TotalStoryBugs,
  CASE 
    WHEN (TotalBugsDefects + TotalStoryBugs) > 0 
    THEN CAST(TotalStoryBugs AS DECIMAL(10,1)) / CAST((TotalBugsDefects + TotalStoryBugs) AS DECIMAL(10,1))
    ELSE 0 
  END AS QA_Efficiency
FROM QA_Metrics;