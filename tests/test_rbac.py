import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestRBAC:

    async def test_member_cannot_invite_users(
        self, client: AsyncClient, admin_token: str, member_token: str, org_id: int
    ):
        # First get member into the org
        await client.post(
            f"/api/v1/organizations/{org_id}/user",
            json={"email": "member@test.com", "role": "member"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        # Member tries to invite someone — must fail
        resp = await client.post(
            f"/api/v1/organizations/{org_id}/user",
            json={"email": "another@test.com", "role": "member"},
            headers={"Authorization": f"Bearer {member_token}"},
        )
        assert resp.status_code == 403

    async def test_member_cannot_list_all_users(
        self, client: AsyncClient, admin_token: str, member_token: str, org_id: int
    ):
        await client.post(
            f"/api/v1/organizations/{org_id}/user",
            json={"email": "member@test.com", "role": "member"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        resp = await client.get(
            f"/api/v1/organizations/{org_id}/users",
            headers={"Authorization": f"Bearer {member_token}"},
        )
        assert resp.status_code == 403

    async def test_member_cannot_view_audit_logs(
        self, client: AsyncClient, admin_token: str, member_token: str, org_id: int
    ):
        await client.post(
            f"/api/v1/organizations/{org_id}/user",
            json={"email": "member@test.com", "role": "member"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        resp = await client.get(
            f"/api/v1/organizations/{org_id}/audit-logs",
            headers={"Authorization": f"Bearer {member_token}"},
        )
        assert resp.status_code == 403

    async def test_non_member_cannot_access_org(
        self, client: AsyncClient, member_token: str, org_id: int
    ):
        resp = await client.get(
            f"/api/v1/organizations/{org_id}/users",
            headers={"Authorization": f"Bearer {member_token}"},
        )
        assert resp.status_code == 403

    async def test_admin_can_list_users(
        self, client: AsyncClient, admin_token: str, org_id: int
    ):
        resp = await client.get(
            f"/api/v1/organizations/{org_id}/users",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        assert "users" in resp.json()

    async def test_member_can_create_item(
        self, client: AsyncClient, admin_token: str, member_token: str, org_id: int
    ):
        await client.post(
            f"/api/v1/organizations/{org_id}/user",
            json={"email": "member@test.com", "role": "member"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        resp = await client.post(
            f"/api/v1/organizations/{org_id}/item",
            json={"item_details": {"name": "Widget", "qty": 5}},
            headers={"Authorization": f"Bearer {member_token}"},
        )
        assert resp.status_code == 201
        assert "item_id" in resp.json()

    async def test_member_sees_only_own_items(
        self, client: AsyncClient, admin_token: str, member_token: str, org_id: int
    ):
        await client.post(
            f"/api/v1/organizations/{org_id}/user",
            json={"email": "member@test.com", "role": "member"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        # Admin creates an item
        await client.post(
            f"/api/v1/organizations/{org_id}/item",
            json={"item_details": {"owner": "admin"}},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        # Member creates their own item
        await client.post(
            f"/api/v1/organizations/{org_id}/item",
            json={"item_details": {"owner": "member"}},
            headers={"Authorization": f"Bearer {member_token}"},
        )
        # Member lists — should only see their own
        resp = await client.get(
            f"/api/v1/organizations/{org_id}/item",
            headers={"Authorization": f"Bearer {member_token}"},
        )
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert all(i["item_details"]["owner"] == "member" for i in items)

    async def test_admin_sees_all_items(
        self, client: AsyncClient, admin_token: str, member_token: str, org_id: int
    ):
        await client.post(
            f"/api/v1/organizations/{org_id}/user",
            json={"email": "member@test.com", "role": "member"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        await client.post(
            f"/api/v1/organizations/{org_id}/item",
            json={"item_details": {"src": "admin"}},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        await client.post(
            f"/api/v1/organizations/{org_id}/item",
            json={"item_details": {"src": "member"}},
            headers={"Authorization": f"Bearer {member_token}"},
        )
        resp = await client.get(
            f"/api/v1/organizations/{org_id}/item",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["total"] >= 2