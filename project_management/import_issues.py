import csv
import os
import requests # type: ignore

# -------------------------------
# Environment variables
# -------------------------------
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_OWNER = os.getenv("GITHUB_OWNER")
GITHUB_REPO = os.getenv("GITHUB_REPO")

PROJECT_ID = os.getenv("PROJECT_ID")
STATUS_FIELD_ID = os.getenv("STATUS_FIELD_ID")
BACKLOG_OPTION_ID = os.getenv("BACKLOG_OPTION_ID")
START_DATE_FIELD_ID = os.getenv("START_DATE_FIELD_ID")
END_DATE_FIELD_ID = os.getenv("END_DATE_FIELD_ID")

CSV_FILE_PATH = "Issues.csv"
GITHUB_API_URL = "https://api.github.com"
GITHUB_GRAPHQL_URL = "https://api.github.com/graphql"

HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

def create_issue_rest(title, body, labels_list):
    url = f"{GITHUB_API_URL}/repos/{GITHUB_OWNER}/{GITHUB_REPO}/issues"
    payload = {
        "title": title,
        "body": body,
        "labels": labels_list
    }

    response = requests.post(url, headers=HEADERS, json=payload)
    if response.status_code == 201:
        issue_data = response.json()
        print(f"✅ Created issue: {issue_data['html_url']}")
        return issue_data["node_id"]
    else:
        print(f"❌ Failed to create issue. Status code: {response.status_code}")
        print(response.json())
        return None

def add_issue_to_project(issue_node_id):
    query = """
    mutation($projectId:ID!, $contentId:ID!) {
        addProjectV2ItemById(input: {
            projectId: $projectId,
            contentId: $contentId
        }) {
            item {
                id
            }
        }
    }
    """
    variables = {
        "projectId": PROJECT_ID,
        "contentId": issue_node_id
    }

    response = requests.post(GITHUB_GRAPHQL_URL, headers=HEADERS, json={"query": query, "variables": variables})
    if response.status_code == 200:
        data = response.json()
        if "errors" in data:
            print(f"❌ Failed to add issue to project: {data['errors']}")
            return None
        item_id = data["data"]["addProjectV2ItemById"]["item"]["id"]
        print(f"✅ Issue added to project. itemId: {item_id}")
        return item_id
    else:
        print(f"❌ Failed to add issue to project. Status code: {response.status_code}")
        print(response.json())
        return None

def update_status_field(item_id):
    query = """
    mutation($projectId:ID!, $itemId:ID!, $fieldId:ID!, $optionId: String!) {
        updateProjectV2ItemFieldValue(input: {
            projectId: $projectId,
            itemId: $itemId,
            fieldId: $fieldId,
            value: { singleSelectOptionId: $optionId }
        }) {
            projectV2Item {
                id
            }
        }
    }
    """
    variables = {
        "projectId": PROJECT_ID,
        "itemId": item_id,
        "fieldId": STATUS_FIELD_ID,
        "optionId": BACKLOG_OPTION_ID
    }

    response = requests.post(GITHUB_GRAPHQL_URL, headers=HEADERS, json={"query": query, "variables": variables})
    if response.status_code == 200:
        data = response.json()
        if "errors" in data:
            print(f"❌ Failed to update Status: {data['errors']}")
        else:
            print("✅ Status updated to Backlog.")
    else:
        print(f"❌ Failed to update Status. Status code: {response.status_code}")
        print(response.json())

def update_date_field(item_id, field_id, date_value):
    if not date_value:
        return

    query = """
    mutation($projectId:ID!, $itemId:ID!, $fieldId:ID!, $date:Date!) {
        updateProjectV2ItemFieldValue(input: {
            projectId: $projectId,
            itemId: $itemId,
            fieldId: $fieldId,
            value: { date: $date }
        }) {
            projectV2Item {
                id
            }
        }
    }
    """
    variables = {
        "projectId": PROJECT_ID,
        "itemId": item_id,
        "fieldId": field_id,
        "date": date_value
    }

    response = requests.post(GITHUB_GRAPHQL_URL, headers=HEADERS, json={"query": query, "variables": variables})
    if response.status_code == 200:
        data = response.json()
        if "errors" in data:
            print(f"❌ Failed to update Date ({field_id}): {data['errors']}")
        else:
            print(f"✅ Date {field_id} updated to {date_value}.")
    else:
        print(f"❌ Failed to update Date. Status code: {response.status_code}")
        print(response.json())

def import_issues_from_csv(csv_path):
    with open(csv_path, mode="r", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            title = row.get("Title", "").strip()
            body = row.get("Body", "").strip()
            labels = row.get("Labels", "").strip()
            start_date = row.get("Start Date", "").strip()
            end_date = row.get("End Date", "").strip()

            labels_list = [lbl.strip() for lbl in labels.split(",") if lbl.strip()]

            # 1. Create Issue
            issue_node_id = create_issue_rest(title, body, labels_list)
            if not issue_node_id:
                continue

            # 2. Add to Project
            item_id = add_issue_to_project(issue_node_id)
            if not item_id:
                continue

            # 3. Set Status to Backlog
            update_status_field(item_id)

            # 4. Set Start/End Dates
            update_date_field(item_id, START_DATE_FIELD_ID, start_date)
            update_date_field(item_id, END_DATE_FIELD_ID, end_date)

if __name__ == "__main__":
    missing_env = [
        var for var in [
            "GITHUB_TOKEN", "GITHUB_OWNER", "GITHUB_REPO",
            "PROJECT_ID", "STATUS_FIELD_ID", "BACKLOG_OPTION_ID",
            "START_DATE_FIELD_ID", "END_DATE_FIELD_ID"
        ] if not os.getenv(var)
    ]

    if missing_env:
        print("❌ Missing environment variables:", ", ".join(missing_env))
        exit(1)

    import_issues_from_csv(CSV_FILE_PATH)
