"""Progress across sessions, encoded into the page link (and a downloadable file). No server storage."""
import base64
import json
import zlib

MAX_SESSIONS = 30


def encode(sessions):
    raw = json.dumps(sessions[-MAX_SESSIONS:], separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(zlib.compress(raw, 9)).decode().rstrip("=")


def decode(code):
    try:
        code = (code or "").strip()
        data = json.loads(zlib.decompress(base64.urlsafe_b64decode(code + "=" * (-len(code) % 4))))
        return [s for s in data if isinstance(s, dict) and "score" in s][-MAX_SESSIONS:] if isinstance(data, list) else []
    except Exception:
        return []
