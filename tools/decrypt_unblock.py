"""Decrypt config/unblock-command-encrypted -> config/unblock-command.txt.

Flow:
  1. Ask for password (checked against config/password.hash).
  2. Correct: wait WAIT_SECONDS, then ask for the password again.
  3. Wrong (at any step): LOCKOUT_SECONDS lockout (saved on disk, so restarting
     does not skip it), then start over.
  4. Correct twice: write unblock-command.txt, wait 5 minutes, delete it.

Usage: python tools/decrypt_unblock.py
"""
import getpass
import json
import sys
import time
from datetime import datetime
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

import password_check

ROOT = Path(__file__).resolve().parent.parent
PLAIN = ROOT / "config" / "unblock-command.txt"
ENCRYPTED = ROOT / "config" / "unblock-command-encrypted"
LOCKOUT_FILE = ROOT / "state" / "decrypt_lockout.json"
STATUS_FILE = ROOT / "state" / "status.json"
LOG_FILE = ROOT / "logs" / "SeeUat4.log"

LOCKOUT_SECONDS = 2 * 60  # after a wrong password
WAIT_SECONDS = 2 * 60  # after a correct first password
KEEP_SECONDS = 5 * 60


def log(message: str) -> None:
    """Append a line to logs/SeeUat4.log (same format as Lock.ps1). Never log passwords."""
    LOG_FILE.parent.mkdir(exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(f"{datetime.now():%Y-%m-%d %H:%M:%S} - {message}\n")


def set_status_unlocked() -> None:
    STATUS_FILE.parent.mkdir(exist_ok=True)
    STATUS_FILE.write_text(json.dumps({
        "mode": "UNLOCKED",
        "unlockedAt": datetime.now().isoformat(timespec="seconds"),
        "unlockedBy": getpass.getuser(),
    }, indent=4), encoding="utf-8")


def countdown(seconds: float, label: str) -> None:
    end = time.time() + seconds
    while True:
        left = int(end - time.time())
        if left <= 0:
            break
        print(f"\r{label} {left // 60:02d}:{left % 60:02d} ", end="", flush=True)
        time.sleep(1)
    print()


def lockout_left() -> float:
    try:
        until = json.loads(LOCKOUT_FILE.read_text())["until"]
    except (OSError, ValueError, KeyError):
        return 0
    return max(0, until - time.time())


def start_lockout() -> None:
    LOCKOUT_FILE.parent.mkdir(exist_ok=True)
    LOCKOUT_FILE.write_text(json.dumps({"until": time.time() + LOCKOUT_SECONDS}))


def main() -> int:
    for f in (ENCRYPTED, password_check.HASH_FILE):
        if not f.exists():
            print(f"Missing {f}", file=sys.stderr)
            return 1

    if PLAIN.exists():
        PLAIN.unlink()
        log("DECRYPT LEFTOVER unblock-command.txt deleted at startup")
        print(f"Deleted leftover {PLAIN.name} from an earlier run.")

    def ask(prompt: str) -> str | None:
        """Return the password if correct, else None (and start a lockout)."""
        print("Type the password phrase exactly, then press Enter.")
        pw = input(prompt).strip()
        if password_check.verify(pw):
            return pw
        print(f"WRONG password. {LOCKOUT_SECONDS // 60} minute lockout starts now.")
        log(f"DECRYPT WRONG PASSWORD - {LOCKOUT_SECONDS // 60} minute lockout started")
        start_lockout()
        return None

    while True:
        left = lockout_left()
        if left > 0:
            print("Locked out. Wait before trying again.")
            countdown(left, "Time left:")
        if ask("Password: ") is None:
            continue
        print(f"Password OK. Wait {WAIT_SECONDS // 60} minutes, then confirm it again.")
        log("DECRYPT first password OK - waiting before confirmation")
        countdown(WAIT_SECONDS, "Confirm in:")
        pw = ask("Password again: ")
        if pw is not None:
            break

    try:
        data = ENCRYPTED.read_bytes()
        plain = Fernet(password_check.derive_key(pw, data[:16])).decrypt(data[16:])
    except InvalidToken:
        log("DECRYPT FAILED corrupted file")
        print("Decrypt failed: corrupted file or file made with another password.",
              file=sys.stderr)
        return 1

    LOCKOUT_FILE.unlink(missing_ok=True)
    PLAIN.write_bytes(plain)
    set_status_unlocked()
    log("DECRYPT SUCCESS - unblock-command.txt written, status UNLOCKED")
    print(f"Wrote {PLAIN}")
    print("Run it now. File will be deleted in 5 minutes. Keep this window open.")
    try:
        countdown(KEEP_SECONDS, "Deleting in:")
    finally:
        PLAIN.unlink(missing_ok=True)
        log("DECRYPT unblock-command.txt deleted")
        print(f"Deleted {PLAIN}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
