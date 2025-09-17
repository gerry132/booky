# messaging/tests/test_moderation_optional.py
import pytest
from django.urls import reverse


def have_endpoint(client, path):
    r = client.options(path)
    return r.status_code in (200, 204, 405)  # OPTIONS may be 200 or 204; 405 means path exists but method not allowed


@pytest.mark.django_db
def test_toggle_mute_optional(auth_client_a, conversation):
    path = f"/api/messages/conversations/{conversation.id}/mute/"
    if not have_endpoint(auth_client_a, path):
        pytest.skip("Mute endpoint not present.")
    # Toggle ON
    r = auth_client_a.post(path, {"value": True}, format="json")
    assert r.status_code in (200, 204)
    # Toggle OFF
    r2 = auth_client_a.post(path, {"value": False}, format="json")
    assert r2.status_code in (200, 204)

@pytest.mark.django_db
def test_block_unblock_optional(auth_client_a, auth_client_b, conversation):
    list_path = "/api/messages/blocks/"
    # Probe endpoint existence
    probe = auth_client_a.options(list_path)
    if probe.status_code not in (200, 204, 405):
        pytest.skip("Blocks API not present.")

    other_username = conversation.seller.username

    # Create block (payload accepts username per your UI; adjust if API expects user id)
    create = auth_client_a.post(list_path, {"blocked": other_username}, format="json")
    assert create.status_code in (200, 201)
    created = create.json() if create.content else {}

    # Prefer id from creation response if available
    block_id = created.get("id")

    if not block_id:
        # Fallback: fetch list and normalize to a list of rows
        lst_resp = auth_client_a.get(list_path)
        assert lst_resp.status_code == 200
        payload = lst_resp.json()

        # Normalize: could be list OR paginated dict {"results": [...]}
        if isinstance(payload, list):
            rows = payload
        elif isinstance(payload, dict):
            # common keys: results / data / items
            rows = (
                payload.get("results")
                or payload.get("data")
                or payload.get("items")
                or []
            )
            if isinstance(rows, dict):  # extremely nested shapes
                rows = rows.get("results", [])
        else:
            rows = []

        # Try to find by a few possible field names
        def is_match(row):
            # supported shapes:
            #  - {"blocked_username": "bob"}
            #  - {"blocked_user": {"username": "bob"}}
            #  - {"blocked": "bob"}  # some APIs mirror username here
            #  - {"blocked": 123, "blocked_username": "bob"}  # id + username
            if not isinstance(row, dict):
                return False
            if row.get("blocked_username") == other_username:
                return True
            bu = row.get("blocked_user")
            if isinstance(bu, dict) and bu.get("username") == other_username:
                return True
            if row.get("blocked") == other_username:
                return True
            return False

        match = next((r for r in rows if is_match(r)), None)
        assert match, "Block not found in listing (schema mismatch?)."
        block_id = match.get("id")

    assert block_id, "Could not resolve block id."

    # Unblock
    delete = auth_client_a.delete(f"{list_path}{block_id}/")
    assert delete.status_code in (200, 204)



@pytest.mark.django_db
def test_report_optional(auth_client_a, conversation):
    path = "/api/messages/reports/"
    if not have_endpoint(auth_client_a, path):
        pytest.skip("Reports endpoint not present.")
    other = conversation.seller.username
    r = auth_client_a.post(path, {
        "reported": other,
        "conversation": conversation.id,
        "reason": "Abuse",
        "details": "Spam content"
    }, format="json")
    assert r.status_code in (200, 201)
