import json
import os
from datetime import datetime, timedelta
import boto3
import requests

# Configuración de variables sensibles movidas a un archivo externo (no incluido en el repo)
try:
    import config
    EMAIL, API_TOKEN, BASE_URL, PROJECT_KEY = config.Email, config.Token, config.URL_B, 'PE'
    AWS_ACCESS_KEY, AWS_SECRET_KEY = config.awsid, config.awskey
except ImportError:
    EMAIL = API_TOKEN = BASE_URL = PROJECT_KEY = AWS_ACCESS_KEY = AWS_SECRET_KEY = 'REDACTED'

RAW_CHANGELOGS_DIR = "raw_changelogs"
FILE_NAME = "my_db.jsonl"
BUCKET_NAME = "jira-issues-raw-data"
os.makedirs(RAW_CHANGELOGS_DIR, exist_ok=True)

def get_issues():
    issues, start_at, max_results = [], 0, 100
    start_date, end_date = datetime.now() - timedelta(days=90), datetime.now()
    jql = (
        f'project={PROJECT_KEY} '
        f'AND ((Type = "Story" AND status WAS "In QA") OR (Type IN ("Story Bug", "Defect"))) '
        f'AND created >= "{start_date:%Y-%m-%d}" AND created <= "{end_date:%Y-%m-%d}" '
        f'ORDER BY created ASC'
    )

    while True:
        response = requests.get(
            f'{BASE_URL}/rest/api/3/search?jql={jql}&fields=*all&startAt={start_at}&maxResults={max_results}',
            auth=(EMAIL, API_TOKEN), headers={'Accept': 'application/json'}
        )

        if response.status_code != 200:
            print(f"Error from Jira API: {response.status_code} - {response.text}")
            break

        data = response.json()
        if "issues" not in data:
            print("Missing 'issues' in response:", data)
            break

        issues.extend(data["issues"])
        if start_at + max_results >= data["total"]:
            break
        start_at += max_results

    return issues

def get_issue_changelog(issue_id):
    response = requests.get(
        f'{BASE_URL}/rest/api/3/issue/{issue_id}?expand=changelog',
        auth=(EMAIL, API_TOKEN), headers={'Accept': 'application/json'}
    )
    response.raise_for_status()
    return response.json().get('changelog', {}).get('histories', [])

def serialize_date(field_value):
    return datetime.strptime(field_value, "%Y-%m-%dT%H:%M:%S.%f%z").strftime("%Y-%m-%d") if field_value else None

def extract_details(issue):
    fields = issue.get('fields', {})
    changelog = get_issue_changelog(issue.get("key"))
    status_changes = []

    # Campos personalizados
    root_cause = fields.get("customfield_10045", {}).get("value", "Not Specified")
    story_bug_root_cause = fields.get("customfield_10050", {}).get("value", "Not Specified")
    severity = fields.get("customfield_10038", {}).get("value", "Not Specified")

    for history in changelog:
        for item in history.get("items", []):
            if item.get("field") == "status":
                status_changes.append({
                    "from": item.get("fromString"),
                    "to": item.get("toString"),
                    "date": history.get("created")
                })

    affected_versions = [v['name'] for v in fields.get('versions', [])] or ["Not Specified"]
    fix_versions = [v['name'] for v in fields.get('fixVersions', [])]
    resolved_in_same_release = any(av in fix_versions for av in affected_versions)

    created_date = fields.get("created")
    resolution_date = fields.get("resolutiondate")

    try:
        created_date = datetime.strptime(created_date, "%Y-%m-%dT%H:%M:%S.%f%z") if created_date else None
        resolution_date = datetime.strptime(resolution_date, "%Y-%m-%dT%H:%M:%S.%f%z") if resolution_date else None
        is_hotfix = resolved_in_same_release and (resolution_date - created_date).days <= 7 if resolution_date else False
    except TypeError:
        is_hotfix = False

    return {
        "id": issue.get("id"),
        "key": issue.get("key"),
        "status": fields.get("status", {}).get("name"),
        "components": [c['name'] for c in fields.get('components', [])],
        "summary": fields.get("summary"),
        "priority": fields.get("priority", {}).get("name"),
        "assignee": fields.get('assignee', {}).get('displayName', 'Unassigned') if fields.get('assignee') else 'Unassigned',
        "reporter": fields.get('reporter', {}).get('displayName', 'Unknown'),
        "created": serialize_date(fields.get("created")),
        "updated": serialize_date(fields.get("updated")),
        "resolutiondate": serialize_date(fields.get("resolutiondate")),
        "Root Cause[Dropdown]": root_cause,
        "labels": fields.get("labels", ["Not Specified"]),
        "Story Bug Root Cause[Dropdown]": story_bug_root_cause,
        "affectedVersions": affected_versions,
        "fixVersions": fix_versions,
        "type": fields.get('issuetype', {}).get('name', 'Unknown'),
        "status_changes": status_changes,
        "resolvedInSameRelease": resolved_in_same_release,
        "isHotfix": is_hotfix,
        "Severity[Dropdown]": severity,
    }

def export_to_jsonl(issues, file_path):
    with open(file_path, 'w') as file:
        for issue in issues:
            file.write(json.dumps(issue) + '\n')

def upload_to_s3(file_path, bucket, folder="all_issues"):
    s3_client = boto3.client('s3', aws_access_key_id=AWS_ACCESS_KEY, aws_secret_access_key=AWS_SECRET_KEY)
    object_name = f"{folder}/{os.path.basename(file_path)}"
    s3_client.upload_file(file_path, bucket, object_name)

# Flujo principal
if __name__ == "__main__":
    issues = get_issues()
    details = [extract_details(issue) for issue in issues]
    output_path = os.path.join(RAW_CHANGELOGS_DIR, FILE_NAME)
    export_to_jsonl(details, output_path)
    upload_to_s3(output_path, BUCKET_NAME)
