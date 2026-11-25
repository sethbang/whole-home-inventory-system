"""Password hashing compatibility after dropping passlib (v3.3.x -> bcrypt).

The golden hashes below were produced by the previous implementation,
``passlib.context.CryptContext(schemes=["bcrypt"])`` (passlib 1.7.4 on
bcrypt 3.2.2). Existing users' stored hashes look exactly like these, so the
new code must keep verifying them, including passlib's silent truncation of
passwords longer than 72 bytes.
"""

import pytest

from app import models, security

SHORT_PW = "super-secret-pw"
SHORT_HASH = "$2b$12$JyMBKRbvitfwhHAj92kanO8rVWodypnrBlvQbZ5Pau.w3zNAEabzS"

LONG_PW = "correct horse battery staple " * 4  # 116 bytes
LONG_HASH = "$2b$12$eYw8845.uQ.tNoqrz6GdBekkXwTAIgb1bFGlxIKG0.hnTI1tOsldm"

LEGACY_2A_PW = "legacy-2a-pw"
LEGACY_2A_HASH = "$2a$12$6toRbXux8IWsLCx4Yvp7UO1djIGyZAhP4wPhxT52GyAqsZezbRNsy"

# 101 UTF-8 bytes; the 72-byte cut lands inside a multi-byte character.
UNICODE_PW = "pässwörd-ünïcode-" + "é" * 40
UNICODE_HASH = "$2b$12$PwXJilHH2snV4gs6fD7lEupEZ/I5FjHx7sWAr09DoYgCvMAsQHAj6"


@pytest.mark.parametrize(
    "password,stored",
    [
        (SHORT_PW, SHORT_HASH),
        (LONG_PW, LONG_HASH),
        (LEGACY_2A_PW, LEGACY_2A_HASH),
        (UNICODE_PW, UNICODE_HASH),
    ],
    ids=["short", "over-72-bytes", "2a-ident", "unicode-over-72-bytes"],
)
def test_verifies_hashes_made_by_passlib(password, stored):
    assert security.verify_password(password, stored)
    assert not security.verify_password("wrong-password", stored)


def test_long_password_still_matches_on_first_72_bytes():
    # Same behavior passlib had: bytes past 72 are ignored.
    assert security.verify_password(LONG_PW + "anything", LONG_HASH)


def test_hash_round_trip():
    hashed = security.get_password_hash(SHORT_PW)
    assert hashed.startswith("$2b$")
    assert security.verify_password(SHORT_PW, hashed)
    assert not security.verify_password("nope", hashed)


@pytest.mark.parametrize("stored", ["", "not-a-bcrypt-hash"])
def test_malformed_stored_hash_fails_closed(stored):
    assert security.verify_password(SHORT_PW, stored) is False


def test_register_rejects_password_over_72_bytes(client):
    resp = client.post(
        "/api/register",
        json={"email": "long@example.com", "username": "long", "password": "é" * 37},
    )
    assert resp.status_code == 422


def test_register_accepts_password_of_exactly_72_bytes(client):
    resp = client.post(
        "/api/register",
        json={"email": "edge@example.com", "username": "edge", "password": "a" * 72},
    )
    assert resp.status_code in (200, 201)


def test_existing_user_with_long_password_can_still_log_in(client, db_session):
    # The lockout scenario: a user registered under passlib with a >72-byte
    # password must still get a token after the switch to bcrypt>=5.
    db_session.add(
        models.User(
            email="legacy@example.com",
            username="legacy",
            hashed_password=LONG_HASH,
            is_active=True,
        )
    )
    db_session.commit()

    resp = client.post(
        "/api/token",
        data={"username": "legacy", "password": LONG_PW},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert resp.status_code == 200, resp.text
