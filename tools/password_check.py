"""Password hashing helpers. The password itself is never stored, only its hash."""
import base64
import hashlib
import hmac
import json
import os
from pathlib import Path

HASH_FILE = Path(__file__).resolve().parent.parent / "config" / "password.hash"
_N, _R, _P = 2**15, 8, 1


def _scrypt(password: str, salt: bytes) -> bytes:
    return hashlib.scrypt(password.encode("utf-8"), salt=salt, n=_N, r=_R, p=_P,
                          maxmem=64 * 1024 * 1024, dklen=32)


def save_hash(password: str) -> None:
    salt = os.urandom(16)
    HASH_FILE.write_text(json.dumps({
        "salt": base64.b64encode(salt).decode(),
        "hash": base64.b64encode(_scrypt(password, salt)).decode(),
    }), encoding="ascii")


def verify(password: str) -> bool:
    data = json.loads(HASH_FILE.read_text(encoding="ascii"))
    salt = base64.b64decode(data["salt"])
    return hmac.compare_digest(_scrypt(password, salt), base64.b64decode(data["hash"]))


def derive_key(password: str, salt: bytes) -> bytes:
    """Fernet key made from the password. No key is stored anywhere."""
    return base64.urlsafe_b64encode(_scrypt(password, salt))
