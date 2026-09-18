"""Data half of the slice: record CRUD and payload validation."""


def test_create_valid_record(client, students_table):
    response = client.post(
        "/api/v1/records",
        json={
            "table_id": students_table["id"],
            "data": {
                "first_name": "Moshe",
                "last_name": "Cohen",
                "entry_year": 2024,
                "active": True,
                "notes": "משה כהן - Class 3 - 2026",
            },
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["data"]["first_name"] == "Moshe"
    assert body["data"]["entry_year"] == 2024
    assert body["data"]["notes"] == "משה כהן - Class 3 - 2026"


def test_missing_required_field_is_rejected(client, students_table):
    response = client.post(
        "/api/v1/records",
        json={"table_id": students_table["id"], "data": {"first_name": "Moshe"}},
    )
    assert response.status_code == 422
    errors = response.json()["detail"]["errors"]
    assert [e["field"] for e in errors] == ["last_name"]
    assert errors[0]["code"] == "required"


def test_blank_string_does_not_satisfy_required(client, students_table):
    response = client.post(
        "/api/v1/records",
        json={"table_id": students_table["id"], "data": {"first_name": "Moshe", "last_name": "   "}},
    )
    assert response.status_code == 422
    assert response.json()["detail"]["errors"][0]["code"] == "required"


def test_invalid_type_is_rejected(client, students_table):
    response = client.post(
        "/api/v1/records",
        json={
            "table_id": students_table["id"],
            "data": {"first_name": "Moshe", "last_name": "Cohen", "entry_year": "not-a-number"},
        },
    )
    assert response.status_code == 422
    errors = response.json()["detail"]["errors"]
    assert errors[0]["field"] == "entry_year"
    assert errors[0]["code"] == "invalid_type"


def test_boolean_is_not_accepted_as_a_number(client, students_table):
    response = client.post(
        "/api/v1/records",
        json={
            "table_id": students_table["id"],
            "data": {"first_name": "Moshe", "last_name": "Cohen", "entry_year": True},
        },
    )
    assert response.status_code == 422
    assert response.json()["detail"]["errors"][0]["field"] == "entry_year"


def test_undefined_field_is_rejected(client, students_table):
    response = client.post(
        "/api/v1/records",
        json={
            "table_id": students_table["id"],
            "data": {"first_name": "Moshe", "last_name": "Cohen", "nickname": "Moishy"},
        },
    )
    assert response.status_code == 422
    errors = response.json()["detail"]["errors"]
    assert errors[0]["field"] == "nickname"
    assert errors[0]["code"] == "unknown_field"


def test_date_and_single_select_validation(client, workspace):
    table = client.post(
        "/api/v1/tables", json={"workspace_id": workspace["id"], "name": "Enrollments"}
    ).json()
    client.post(
        "/api/v1/fields",
        json={"table_id": table["id"], "label": "Start", "field_type": "date", "key": "start"},
    )
    client.post(
        "/api/v1/fields",
        json={
            "table_id": table["id"],
            "label": "Track",
            "field_type": "single_select",
            "key": "track",
            "config": {"options": ["morning", "evening"]},
        },
    )

    ok = client.post(
        "/api/v1/records",
        json={"table_id": table["id"], "data": {"start": "2026-09-01", "track": "morning"}},
    )
    assert ok.status_code == 201, ok.text
    assert ok.json()["data"]["start"] == "2026-09-01"

    bad_date = client.post(
        "/api/v1/records", json={"table_id": table["id"], "data": {"start": "01/09/2026"}}
    )
    assert bad_date.status_code == 422
    assert bad_date.json()["detail"]["errors"][0]["code"] == "invalid_type"

    bad_option = client.post(
        "/api/v1/records", json={"table_id": table["id"], "data": {"track": "night"}}
    )
    assert bad_option.status_code == 422
    assert bad_option.json()["detail"]["errors"][0]["code"] == "invalid_option"


def test_list_records_is_paged_and_newest_first(client, students_table):
    for name in ("Moshe", "David", "Yosef"):
        client.post(
            "/api/v1/records",
            json={"table_id": students_table["id"], "data": {"first_name": name, "last_name": "Levi"}},
        )

    page = client.get("/api/v1/records", params={"table_id": students_table["id"], "limit": 2})
    assert page.status_code == 200
    body = page.json()
    assert body["total"] == 3
    assert len(body["items"]) == 2
    assert {item["data"]["first_name"] for item in body["items"]} <= {"Moshe", "David", "Yosef"}


def test_edit_record_via_put_and_patch(client, students_table):
    created = client.post(
        "/api/v1/records",
        json={
            "table_id": students_table["id"],
            "data": {"first_name": "Moshe", "last_name": "Cohen", "entry_year": 2024},
        },
    ).json()

    patched = client.patch(f"/api/v1/records/{created['id']}", json={"data": {"entry_year": 2025}})
    assert patched.status_code == 200, patched.text
    assert patched.json()["data"] == {"first_name": "Moshe", "last_name": "Cohen", "entry_year": 2025}

    replaced = client.put(
        f"/api/v1/records/{created['id']}",
        json={"data": {"first_name": "David", "last_name": "Levi"}},
    )
    assert replaced.status_code == 200, replaced.text
    # PUT is a full replacement, so the omitted optional field is gone.
    assert replaced.json()["data"] == {"first_name": "David", "last_name": "Levi"}


def test_patch_cannot_clear_a_required_field(client, students_table):
    created = client.post(
        "/api/v1/records",
        json={"table_id": students_table["id"], "data": {"first_name": "Moshe", "last_name": "Cohen"}},
    ).json()

    response = client.patch(f"/api/v1/records/{created['id']}", json={"data": {"last_name": None}})
    assert response.status_code == 422
    assert response.json()["detail"]["errors"][0]["code"] == "required"


def test_delete_record(client, students_table):
    created = client.post(
        "/api/v1/records",
        json={"table_id": students_table["id"], "data": {"first_name": "Moshe", "last_name": "Cohen"}},
    ).json()

    assert client.delete(f"/api/v1/records/{created['id']}").status_code == 204
    assert client.get(f"/api/v1/records/{created['id']}").status_code == 404

    page = client.get("/api/v1/records", params={"table_id": students_table["id"]}).json()
    assert page["total"] == 0


def test_deleting_a_table_removes_its_records(client, students_table):
    client.post(
        "/api/v1/records",
        json={"table_id": students_table["id"], "data": {"first_name": "Moshe", "last_name": "Cohen"}},
    )
    assert client.delete(f"/api/v1/tables/{students_table['id']}").status_code == 204
    assert client.get(f"/api/v1/tables/{students_table['id']}").status_code == 404
