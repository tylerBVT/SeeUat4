"""Encrypt config/unblock-command.txt -> config/unblock-command-encrypted.

The key comes from the password phrase. No key file.
File format: salt (16 bytes) + Fernet token.

Usage: python tools/encrypt_unblock.py
"""
import os
import sys
from pathlib import Path

from cryptography.fernet import Fernet

import password_check

ROOT = Path(__file__).resolve().parent.parent
PLAIN = ROOT / "config" / "unblock-command.txt"
ENCRYPTED = ROOT / "config" / "unblock-command-encrypted"


def main() -> int:
    if not PLAIN.exists():
        print(f"Missing {PLAIN}", file=sys.stderr)
        return 1
    if not password_check.HASH_FILE.exists():
        print("Missing password.hash. Run make_password_hash.py first.", file=sys.stderr)
        return 1
    print("Type the password phrase, then press Enter (text is visible).")
    pw = input("Password: ").strip()
    if not password_check.verify(pw):
        print("ERROR: does not match password.hash. Nothing saved.", file=sys.stderr)
        return 1
    salt = os.urandom(16)
    token = Fernet(password_check.derive_key(pw, salt)).encrypt(PLAIN.read_bytes())
    ENCRYPTED.write_bytes(salt + token)
    print(f"Encrypted {PLAIN.name} -> {ENCRYPTED}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
