"""Local API + web server for the SeeUat4 UI.

Does the same unlock flow as tools/decrypt_unblock.py (same password hash,
same lockout file, same log and status files), but over HTTP for the Angular UI.

Usage: py server\\server.py   then open http://127.0.0.1:8765
Dev:   run this, plus `npm start` in frontend/ (proxy to this server).
"""
import atexit
import json
import math
import mimetypes
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from cryptography.fernet import Fernet, InvalidToken  # noqa: E402

import decrypt_unblock as du  # noqa: E402
import password_check  # noqa: E402

HOST, PORT = "127.0.0.1", 8765
ALLOWED_HOSTS = {"127.0.0.1", "localhost"}
WEB_ROOT = ROOT / "frontend" / "dist" / "frontend" / "browser"
HOSTS_FILE = Path(r"C:\Windows\System32\drivers\etc\hosts")


def build_lock_command() -> str:
    script = ROOT / "script" / "Lock.ps1"
    try:
        path = "$HOME\\" + str(script.relative_to(Path.home()))
    except ValueError:
        path = str(script)
    return ("Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force; "
            f'& "{path}"')


LOCK_COMMAND = build_lock_command()


class Unlock:
    """In-memory phase of the unlock flow. A server restart resets it (safe)."""

    def __init__(self) -> None:
        self.mutex = threading.RLock()
        self.wait_until: float | None = None
        self.delete_at: float | None = None
        self.command: str | None = None

    def state(self) -> dict:
        now = time.time()
        with self.mutex:
            left = du.lockout_left()
            if left > 0:
                return {"phase": "lockout", "secondsLeft": math.ceil(left)}
            if self.delete_at and now < self.delete_at:
                return {"phase": "unlocked", "secondsLeft": math.ceil(self.delete_at - now),
                        "command": self.command}
            if self.wait_until:
                if now < self.wait_until:
                    return {"phase": "waiting", "secondsLeft": math.ceil(self.wait_until - now)}
                return {"phase": "confirm", "secondsLeft": 0}
            return {"phase": "idle", "secondsLeft": 0}

    def _wrong(self) -> tuple[int, dict]:
        self.wait_until = None
        du.start_lockout()
        du.log(f"UI WRONG PASSWORD - {du.LOCKOUT_SECONDS // 60} minute lockout started")
        return 401, {"error": "Wrong password.", "unlock": self.state()}

    def start(self, pw: str) -> tuple[int, dict]:
        with self.mutex:
            if self.state()["phase"] != "idle":
                return 409, {"error": "Not ready for a first password.", "unlock": self.state()}
            if not password_check.verify(pw):
                return self._wrong()
            self.wait_until = time.time() + du.WAIT_SECONDS
            du.log("UI first password OK - waiting before confirmation")
            return 200, {"unlock": self.state()}

    def confirm(self, pw: str) -> tuple[int, dict]:
        with self.mutex:
            if self.state()["phase"] != "confirm":
                return 409, {"error": "Not ready to confirm.", "unlock": self.state()}
            if not password_check.verify(pw):
                return self._wrong()
            try:
                data = du.ENCRYPTED.read_bytes()
                plain = Fernet(password_check.derive_key(pw, data[:16])).decrypt(data[16:])
            except (InvalidToken, OSError):
                du.log("UI DECRYPT FAILED corrupted file")
                return 500, {"error": "Decrypt failed: corrupted file."}
            du.LOCKOUT_FILE.unlink(missing_ok=True)
            du.PLAIN.write_bytes(plain)
            du.set_status_unlocked()
            du.log("UI DECRYPT SUCCESS - unblock-command.txt written, status UNLOCKED")
            self.wait_until = None
            self.command = plain.decode("utf-8")
            self.delete_at = time.time() + du.KEEP_SECONDS
            timer = threading.Timer(du.KEEP_SECONDS, self.expire)
            timer.daemon = True
            timer.start()
            return 200, {"unlock": self.state()}

    def expire(self) -> None:
        with self.mutex:
            du.PLAIN.unlink(missing_ok=True)
            du.log("UI unblock-command.txt deleted")
            self.command = None
            self.delete_at = None


UNLOCK = Unlock()


def hosts_blocked() -> bool:
    try:
        text = HOSTS_FILE.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return True  # cannot read: assume blocked
    return "# SEEuat4_START" in text and "# SEEuat4_END" in text


def last_unlocked_at() -> str | None:
    try:
        return json.loads(du.STATUS_FILE.read_text(encoding="utf-8-sig")).get("unlockedAt")
    except (OSError, ValueError):
        return None


def full_state() -> dict:
    return {
        "mode": "LOCKED" if hosts_blocked() else "UNLOCKED",
        "lastUnlockedAt": last_unlocked_at(),
        "lockCommand": LOCK_COMMAND,
        "unlock": UNLOCK.state(),
    }


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args) -> None:  # quiet
        pass

    def _host_ok(self) -> bool:
        host = (self.headers.get("Host") or "").split(":")[0]
        if host not in ALLOWED_HOSTS:
            return False
        origin = self.headers.get("Origin")
        return origin is None or urlparse(origin).hostname in ALLOWED_HOSTS

    def _send(self, code: int, body: bytes, ctype: str = "application/json") -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code: int, obj: dict) -> None:
        self._send(code, json.dumps(obj).encode("utf-8"))

    def do_GET(self) -> None:
        if not self._host_ok():
            return self._json(403, {"error": "Forbidden host."})
        path = urlparse(self.path).path
        if path == "/api/state":
            return self._json(200, full_state())
        if path.startswith("/api/"):
            return self._json(404, {"error": "Not found."})
        self._static(path)

    def do_POST(self) -> None:
        if not self._host_ok():
            return self._json(403, {"error": "Forbidden host."})
        path = urlparse(self.path).path
        try:
            length = min(int(self.headers.get("Content-Length") or 0), 10_000)
            body = json.loads(self.rfile.read(length) or b"{}")
            pw = str(body.get("password", "")).strip()
        except (ValueError, AttributeError):
            return self._json(400, {"error": "Bad request."})
        if path == "/api/unlock/start":
            code, obj = UNLOCK.start(pw)
        elif path == "/api/unlock/confirm":
            code, obj = UNLOCK.confirm(pw)
        else:
            return self._json(404, {"error": "Not found."})
        self._json(code, obj)

    def _static(self, path: str) -> None:
        rel = path.lstrip("/") or "index.html"
        target = (WEB_ROOT / rel).resolve()
        if WEB_ROOT.resolve() not in target.parents or not target.is_file():
            target = WEB_ROOT / "index.html"  # SPA fallback
        if not target.is_file():
            return self._send(404, b"Frontend not built. Run: npm run build (in frontend/)",
                              "text/plain")
        ctype = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        self._send(200, target.read_bytes(), ctype)


def main() -> int:
    for f in (du.ENCRYPTED, password_check.HASH_FILE):
        if not f.exists():
            print(f"Missing {f}", file=sys.stderr)
            return 1
    if du.PLAIN.exists():
        du.PLAIN.unlink()
        du.log("UI LEFTOVER unblock-command.txt deleted at startup")
    atexit.register(lambda: du.PLAIN.unlink(missing_ok=True))
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"SeeUat4 UI on http://{HOST}:{PORT}  (Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
