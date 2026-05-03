"""
Field-level encryption for sensitive data using Fernet (AES-128-CBC).

Set ENCRYPTION_KEY in your .env file as any plain-text passphrase you can remember:
    ENCRYPTION_KEY=MySecretPassphrase2026

The passphrase is converted to a proper Fernet key via PBKDF2 (100K iterations).
Same passphrase always produces the same key — so your data is always recoverable
as long as you remember the passphrase.
"""
import os
import base64
import hashlib
import logging
from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger("daily_plan")

_SALT = b"dailyplanner-refcards-v1"  # Fixed salt — do not change


def _get_fernet():
    passphrase = os.environ.get("ENCRYPTION_KEY", "").strip()

    if not passphrase:
        logger.warning("ENCRYPTION_KEY not set — encryption disabled, storing plaintext")
        return None

    # Derive a 32-byte key from the passphrase
    derived = hashlib.pbkdf2_hmac("sha256", passphrase.encode(), _SALT, 100_000, dklen=32)
    key = base64.urlsafe_b64encode(derived)
    return Fernet(key)


_fernet = _get_fernet()


def is_active() -> bool:
    """True if ENCRYPTION_KEY was set at import time and a working
    Fernet instance was built. Cheap (no recomputation) — safe to call
    on every request to drive a "vault is unencrypted" warning banner."""
    return _fernet is not None


def encrypt(value):
    if not value or not _fernet:
        return value
    return _fernet.encrypt(str(value).encode()).decode()


def decrypt(token):
    if not token or not _fernet:
        return token
    try:
        return _fernet.decrypt(str(token).encode()).decode()
    except (InvalidToken, Exception):
        # Not encrypted (old data) or wrong key — return as-is
        return token


def encrypt_fields(data, fields):
    for f in fields:
        if f in data and data[f]:
            data[f] = encrypt(data[f])
    return data


def decrypt_fields(data, fields):
    for f in fields:
        if f in data and data[f]:
            data[f] = decrypt(data[f])
    return data


def decrypt_rows(rows, fields):
    for row in rows:
        decrypt_fields(row, fields)
    return rows
