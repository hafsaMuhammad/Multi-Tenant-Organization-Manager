import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestOrganizationIsolation:

    async def _create_org(self, client: AsyncClient, token: str, name: str) -> int:
        resp = await client.post(
            "/api/v1/organizations",
            json={"org_name": name},
            headers={"Authorization": f"Bearer {token}"},
        )
        return resp.json()["org_id"]

    async def test_user_cannot_access_org_they_dont_belong_to(
        self, client: AsyncClient, admin_token: str, member_token: str
    ):
        org_a = await self._create_org(client, admin_token, "Org A")
        resp = await client.get(
            f"/api/v1/organizations/{org_a}/users",
            headers={"Authorization": f"Bearer {member_token}"},
        )
        assert resp.status_code == 403

    async def test_items_isolated_between_orgs(
        self, client: AsyncClient, admin_token: str
    ):
        org_a = await self._create_org(client, admin_token, "Org Alpha")
        org_b = await self._create_org(client, admin_token, "Org Beta")

        await client.post(
            f"/api/v1/organizations/{org_a}/item",
            json={"item_details": {"tag": "belongs_to_a"}},
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        resp = await client.get(
            f"/api/v1/organizations/{org_b}/item",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        # org_b has no items — org_a item must not leak
        assert all(i["org_id"] == org_b for i in resp.json()["items"])

    async def test_audit_logs_isolated_between_orgs(
        self, client: AsyncClient, admin_token: str
    ):
        org_a = await self._create_org(client, admin_token, "Audit Org A")
        org_b = await self._create_org(client, admin_token, "Audit Org B")

        logs_a = (await client.get(
            f"/api/v1/organizations/{org_a}/audit-logs",
            headers={"Authorization": f"Bearer {admin_token}"},
        )).json()

        logs_b = (await client.get(
            f"/api/v1/organizations/{org_b}/audit-logs",
            headers={"Authorization": f"Bearer {admin_token}"},
        )).json()

        ids_a = {log["id"] for log in logs_a}
        ids_b = {log["id"] for log in logs_b}
        assert ids_a.isdisjoint(ids_b)  # no log appears in both

    async def test_user_can_belong_to_multiple_orgs(
        self, client: AsyncClient, admin_token: str, member_token: str
    ):
        org_a = await self._create_org(client, admin_token, "Multi Org A")
        org_b = await self._create_org(client, admin_token, "Multi Org B")

        for org in (org_a, org_b):
            resp = await client.post(
                f"/api/v1/organizations/{org}/user",
                json={"email": "member@test.com", "role": "member"},
                headers={"Authorization": f"Bearer {admin_token}"},
            )
            assert resp.status_code == 201

        # Member can post items to both orgs
        for org in (org_a, org_b):
            resp = await client.post(
                f"/api/v1/organizations/{org}/item",
                json={"item_details": {"tag": f"item_in_{org}"}},
                headers={"Authorization": f"Bearer {member_token}"},
            )
            assert resp.status_code == 201

    async def test_duplicate_invite_rejected(
        self, client: AsyncClient, admin_token: str, member_token: str
    ):
        org = await self._create_org(client, admin_token, "Dup Invite Org")
        await client.post(
            f"/api/v1/organizations/{org}/user",
            json={"email": "member@test.com", "role": "member"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        resp = await client.post(
            f"/api/v1/organizations/{org}/user",
            json={"email": "member@test.com", "role": "member"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 409

    async def test_search_scoped_to_org(
        self, client: AsyncClient, admin_token: str, member_token: str
    ):
        org_a = await self._create_org(client, admin_token, "Search Org A")
        org_b = await self._create_org(client, admin_token, "Search Org B")

        # Member only in org_a
        await client.post(
            f"/api/v1/organizations/{org_a}/user",
            json={"email": "member@test.com", "role": "member"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        # Search in org_b should not find member
        resp = await client.get(
            f"/api/v1/organizations/{org_b}/users/search?q=member",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        emails = [u["email"] for u in resp.json()]
        assert "member@test.com" not in emails