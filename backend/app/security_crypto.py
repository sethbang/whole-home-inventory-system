"""Symmetric encryption helper for at-rest secrets (v3.2).

Used by ``app.services.llm_config`` to encrypt the operator-supplied
LLM API key before it lands in the ``llm_config`` table. The Fernet
key is derived from ``settings.SECRET_KEY`` via HKDF-SHA256 so the
same SECRET_KEY always produces the same Fernet key (idempotent
across restarts), but a SECRET_KEY rotation invalidates every
existing ciphertext — restored backups onto a host with a different
SECRET_KEY will fail to decrypt and the service falls back to env.

Public surface:

* :func:`derive_fernet_key(secret)` — HKDF -> 32-byte key, base64-
  encoded for ``Fernet(...)``.
* :func:`encrypt(plaintext)` / :func:`decrypt(ciphertext)` —
  pull the secret out of ``settings.SECRET_KEY``, derive a key,
  round-trip the value. Strings in, strings out (UTF-8 + base64
  ASCII for the ciphertext).
* :exc:`DecryptionError` — raised when the ciphertext can't be
  decrypted (wrong key, tampered token). Callers catch this to fall
  back to env.
"""

from __future__ import annotations

import logging

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from .settings import settings

logger = logging.getLogger(__name__)

# Fixed info string. Rotating this would invalidate every stored
# ciphertext, so don't.
_HKDF_INFO = b"whis-llm-config-v1"
_HKDF_SALT = b"whis-fernet-salt-v1"


class DecryptionError(Exception):
    """Raised when a Fernet token can't be decrypted."""


def derive_fernet_key(secret: str) -> bytes:
    """Derive a Fernet-compatible key from an arbitrary-length secret.

    HKDF-SHA256 with a fixed salt + info, output truncated to 32 bytes
    and url-safe base64-encoded (the form Fernet's constructor wants).
    Deterministic — same secret always produces the same key — so
    encrypt/decrypt round-trip across processes that share SECRET_KEY.
    """
    if not secret:
        raise ValueError("derive_fernet_key requires a non-empty secret")
    raw = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=_HKDF_SALT,
        info=_HKDF_INFO,
    ).derive(secret.encode("utf-8"))
    # Fernet wants url-safe base64. ``base64.urlsafe_b64encode`` is what
    # ``Fernet.generate_key`` returns under the hood.
    import base64

    return base64.urlsafe_b64encode(raw)


def _fernet() -> Fernet:
    return Fernet(derive_fernet_key(settings.SECRET_KEY))


def encrypt(plaintext: str) -> str:
    """Encrypt a string and return the ASCII-safe Fernet token."""
    if plaintext is None:
        raise ValueError("encrypt requires a non-None plaintext")
    token = _fernet().encrypt(plaintext.encode("utf-8"))
    return token.decode("ascii")


def decrypt(ciphertext: str) -> str:
    """Decrypt a Fernet token. Raises :class:`DecryptionError` on failure."""
    if not ciphertext:
        raise DecryptionError("ciphertext is empty")
    try:
        plaintext = _fernet().decrypt(ciphertext.encode("ascii"))
    except (InvalidToken, ValueError) as exc:
        raise DecryptionError(str(exc)) from exc
    return plaintext.decode("utf-8")
