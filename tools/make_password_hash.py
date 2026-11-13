"""Create config/password.hash from a password you type.

Usage: python tools/make_password_hash.py
"""
import sys

import password_check


def main() -> int:
    print("Type the password phrase, then press Enter (text is visible).")
    pw = input("Password: ").strip()
    if not pw:
        print("Empty password. Nothing saved.", file=sys.stderr)
        return 1
    if input("Type it again: ").strip() != pw:
        print("ERROR: did not match. Nothing saved.", file=sys.stderr)
        return 1
    password_check.save_hash(pw)
    print(f"Saved hash to {password_check.HASH_FILE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
