"""Tests for app.security_crypto."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from app import security_crypto
from app.security_crypto import DecryptionError, decrypt, derive_fernet_key, encrypt


def test_round_trip_returns_original_plaintext() -> None:
    cipher = encrypt("hunter2")
    assert decrypt(cipher) == "hunter2"


def test_round_trip_handles_long_payload() -> None:
    payload = "sk-or-v1-" + "a" * 256
    assert decrypt(encrypt(payload)) == payload


def test_ciphertexts_are_distinct_for_repeated_calls() -> None:
    """Fernet tokens carry an IV; the same plaintext encrypts twice
    to different ciphertexts. Both decrypt back to the same value."""
    a = encrypt("same-value")
    b = encrypt("same-value")
    assert a != b
    assert decrypt(a) == decrypt(b) == "same-value"


def test_derive_fernet_key_is_deterministic() -> None:
    a = derive_fernet_key("the-quick-brown-fox")
    b = derive_fernet_key("the-quick-brown-fox")
    assert a == b
    assert len(a) == 44  # base64 of 32 bytes


def test_derive_fernet_key_changes_with_secret() -> None:
    assert derive_fernet_key("alpha") != derive_fernet_key("beta")


def test_derive_fernet_key_rejects_empty_secret() -> None:
    with pytest.raises(ValueError):
        derive_fernet_key("")


def test_decrypt_with_wrong_secret_raises() -> None:
    cipher = encrypt("secret-value")
    # Patch the settings.SECRET_KEY at the module level so a fresh
    # Fernet builds with a different derived key.
    with patch.object(
        security_crypto.settings, "SECRET_KEY", "a-completely-different-secret-x" * 2
    ):
        with pytest.raises(DecryptionError):
            decrypt(cipher)


def test_decrypt_empty_ciphertext_raises() -> None:
    with pytest.raises(DecryptionError):
        decrypt("")


def test_decrypt_garbage_raises() -> None:
    with pytest.raises(DecryptionError):
        decrypt("definitely-not-a-fernet-token")
