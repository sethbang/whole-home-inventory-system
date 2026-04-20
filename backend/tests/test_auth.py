def test_register_then_login_round_trip(client):
    payload = {"email": "bob@example.com", "username": "bob", "password": "super-secret-pw"}
    reg = client.post("/api/register", json=payload)
    assert reg.status_code == 200, reg.text
    assert reg.json()["username"] == "bob"

    token_resp = client.post(
        "/api/token",
        data={"username": "bob", "password": "super-secret-pw"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert token_resp.status_code == 200
    body = token_resp.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"] and body["access_token"] != "dev_token"


def test_login_wrong_password_is_401(client, user):
    resp = client.post(
        "/api/token",
        data={"username": user.username, "password": "not-the-password"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert resp.status_code == 401
    # Redacted: should never leak whether the account exists or the password length.
    assert "password" not in resp.text.lower() or "incorrect" in resp.text.lower()


def test_users_me_requires_auth(client):
    resp = client.get("/api/users/me")
    assert resp.status_code == 401


def test_users_me_with_token(client, user, auth_headers):
    resp = client.get("/api/users/me", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["username"] == user.username
