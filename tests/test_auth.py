import pytest
@pytest.mark.asyncio
async def test_register_login_and_me(client):
    r = await client.post("/auth/register", json={"name":"Test User","email":"test@example.com","phone":"9999999999","password":"Testing123!"})
    assert r.status_code == 201, r.text
    login = await client.post("/auth/login", json={"email":"test@example.com","password":"Testing123!"})
    assert login.status_code == 200
    token = login.json()["access_token"]
    me = await client.get("/auth/me", headers={"Authorization":f"Bearer {token}"})
    assert me.status_code == 200 and me.json()["email"] == "test@example.com"
@pytest.mark.asyncio
async def test_invalid_token(client):
    r = await client.get("/auth/me", headers={"Authorization":"Bearer definitely.invalid.token"})
    assert r.status_code == 401
@pytest.mark.asyncio
async def test_protected_route_requires_token(client):
    assert (await client.get("/bookings/my")).status_code == 401
