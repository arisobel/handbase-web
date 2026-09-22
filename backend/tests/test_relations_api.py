"""Single-value metadata relations: validation, display and RESTRICT."""


def make_relation(client, workspace):
    statuses = client.post("/api/v1/tables", json={"workspace_id": workspace["id"], "name": "Statuses"}).json()
    client.post("/api/v1/fields", json={"table_id": statuses["id"], "label": "Name", "field_type": "text", "key": "name"})
    projects = client.post("/api/v1/tables", json={"workspace_id": workspace["id"], "name": "Projects"}).json()
    relation = client.post("/api/v1/fields", json={"table_id": projects["id"], "label": "Status", "field_type": "relation", "key": "status", "config": {"target_table_id": statuses["id"]}})
    assert relation.status_code == 201, relation.text
    return statuses, projects


def test_relation_requires_valid_same_workspace_target(client, workspace, other_workspace):
    projects = client.post("/api/v1/tables", json={"workspace_id": workspace["id"], "name": "Projects"}).json()
    missing = client.post("/api/v1/fields", json={"table_id": projects["id"], "label": "Status", "field_type": "relation", "config": {}})
    assert missing.status_code == 422
    invalid = client.post("/api/v1/fields", json={"table_id": projects["id"], "label": "Invalid", "field_type": "relation", "config": {"target_table_id": "00000000-0000-0000-0000-000000000000"}})
    assert invalid.status_code == 422
    foreign_client, foreign = other_workspace
    foreign_table = foreign_client.post("/api/v1/tables", json={"workspace_id": foreign["id"], "name": "Foreign statuses"}).json()
    rejected = client.post("/api/v1/fields", json={"table_id": projects["id"], "label": "Status", "field_type": "relation", "config": {"target_table_id": foreign_table["id"]}})
    assert rejected.status_code == 422
    assert rejected.json()["detail"]["errors"][0]["code"] == "cross_workspace_relation"


def test_relation_validates_displays_and_restricts_delete(client, workspace):
    statuses, projects = make_relation(client, workspace)
    status = client.post("/api/v1/records", json={"table_id": statuses["id"], "data": {"name": "In progress"}}).json()
    project = client.post("/api/v1/records", json={"table_id": projects["id"], "data": {"status": status["id"]}})
    assert project.status_code == 201
    listed = client.get("/api/v1/records", params={"table_id": projects["id"]}).json()
    assert listed["items"][0]["relation_display"]["status"] == "In progress"
    assert client.delete(f"/api/v1/records/{status['id']}").status_code == 409


def test_relation_rejects_missing_or_wrong_target_and_allows_empty(client, workspace):
    statuses, projects = make_relation(client, workspace)
    empty = client.post("/api/v1/records", json={"table_id": projects["id"], "data": {}})
    assert empty.status_code == 201
    missing = client.post("/api/v1/records", json={"table_id": projects["id"], "data": {"status": "00000000-0000-0000-0000-000000000000"}})
    assert missing.status_code == 422
    other = client.post("/api/v1/records", json={"table_id": projects["id"], "data": {}}).json()
    wrong = client.post("/api/v1/records", json={"table_id": projects["id"], "data": {"status": other["id"]}})
    assert wrong.status_code == 422
