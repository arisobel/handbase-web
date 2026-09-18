"""Structural half of the slice: workspaces, tables and field definitions."""


def test_create_workspace(client):
    response = client.post("/api/v1/workspaces", json={"name": "Yeshiva", "default_locale": "he"})
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["name"] == "Yeshiva"
    assert body["default_locale"] == "he"
    assert body["id"]

    listed = client.get("/api/v1/workspaces")
    assert listed.status_code == 200
    assert [w["id"] for w in listed.json()] == [body["id"]]


def test_create_table_with_hebrew_name_gets_neutral_slug(client, workspace):
    response = client.post(
        "/api/v1/tables", json={"workspace_id": workspace["id"], "name": "תלמידים"}
    )
    assert response.status_code == 201, response.text
    table = response.json()
    assert table["name"] == "תלמידים"
    # A Hebrew-only label yields no Latin slug, so a neutral fallback is used.
    assert table["slug"] == "table-1"

    second = client.post("/api/v1/tables", json={"workspace_id": workspace["id"], "name": "מורים"})
    assert second.json()["slug"] == "table-2"

    latin = client.post("/api/v1/tables", json={"workspace_id": workspace["id"], "name": "Famílias"})
    assert latin.json()["slug"] == "familias"


def test_create_table_rejects_unknown_workspace(client):
    response = client.post(
        "/api/v1/tables",
        json={"workspace_id": "00000000-0000-0000-0000-000000000000", "name": "Ghost"},
    )
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "not_found"


def test_create_fields_and_read_them_back(client, workspace):
    table = client.post(
        "/api/v1/tables", json={"workspace_id": workspace["id"], "name": "Students"}
    ).json()

    created = client.post(
        "/api/v1/fields",
        json={"table_id": table["id"], "label": "First name", "field_type": "text", "required": True},
    )
    assert created.status_code == 201, created.text
    field = created.json()
    assert field["key"] == "first_name"
    assert field["required"] is True
    assert field["position"] == 0

    second = client.post(
        "/api/v1/fields",
        json={"table_id": table["id"], "label": "שנת כניסה", "field_type": "number"},
    )
    assert second.status_code == 201
    # No Latin characters in the label: a neutral key is generated instead.
    assert second.json()["key"] == "field_1"
    assert second.json()["position"] == 1

    detail = client.get(f"/api/v1/tables/{table['id']}")
    assert detail.status_code == 200
    assert [f["key"] for f in detail.json()["fields"]] == ["first_name", "field_1"]


def test_create_field_rejects_unsupported_type(client, workspace):
    table = client.post(
        "/api/v1/tables", json={"workspace_id": workspace["id"], "name": "Students"}
    ).json()
    response = client.post(
        "/api/v1/fields",
        json={"table_id": table["id"], "label": "Owner", "field_type": "relation"},
    )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "validation_error"


def test_single_select_requires_options(client, workspace):
    table = client.post(
        "/api/v1/tables", json={"workspace_id": workspace["id"], "name": "Students"}
    ).json()

    without = client.post(
        "/api/v1/fields",
        json={"table_id": table["id"], "label": "Class", "field_type": "single_select"},
    )
    assert without.status_code == 422
    assert without.json()["detail"]["errors"][0]["code"] == "missing_options"

    with_options = client.post(
        "/api/v1/fields",
        json={
            "table_id": table["id"],
            "label": "Class",
            "field_type": "single_select",
            "config": {"options": [{"value": "a", "label": "כיתה א"}, "b"]},
        },
    )
    assert with_options.status_code == 201


def test_duplicate_explicit_field_key_conflicts(client, students_table):
    response = client.post(
        "/api/v1/fields",
        json={"table_id": students_table["id"], "label": "Again", "field_type": "text", "key": "first_name"},
    )
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "conflict"


def test_field_types_catalog_separates_supported_from_planned(client):
    body = client.get("/api/v1/field-types").json()
    assert body["supported"] == ["text", "long_text", "number", "boolean", "date", "single_select"]
    assert "relation" in body["planned"]
    assert not set(body["supported"]) & set(body["planned"])


def test_deleting_a_field_drops_its_key_from_records(client, students_table):
    record = client.post(
        "/api/v1/records",
        json={
            "table_id": students_table["id"],
            "data": {"first_name": "Moshe", "last_name": "Cohen", "notes": "temporary"},
        },
    ).json()

    notes_field = next(f for f in students_table["fields"] if f["key"] == "notes")
    assert client.delete(f"/api/v1/fields/{notes_field['id']}").status_code == 204

    refreshed = client.get(f"/api/v1/records/{record['id']}").json()
    assert "notes" not in refreshed["data"]
    assert refreshed["data"]["first_name"] == "Moshe"
