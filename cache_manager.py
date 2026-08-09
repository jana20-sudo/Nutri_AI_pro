"""
Fixed: Issue 17 - lock dictionary cleanup
"""
import json
import os
import time
import hashlib
import threading
from config import CACHE_DIR, CACHE_EXPIRY_HOURS

os.makedirs(CACHE_DIR, exist_ok=True)

_locks = {}
_lock_manager = threading.Lock()
_lock_access_count = {}
_CLEANUP_THRESHOLD = 200


def _get_lock(path):
    """Fix 17: Cleanup unused locks periodically"""
    with _lock_manager:
        if path not in _locks:
            _locks[path] = threading.Lock()
            _lock_access_count[path] = 0
        _lock_access_count[path] += 1
        # Cleanup locks not used recently
        if len(_locks) > _CLEANUP_THRESHOLD:
            paths_to_remove = [
                p for p, count in
                _lock_access_count.items()
                if count < 2 and p != path
            ]
            for p in paths_to_remove[:50]:
                del _locks[p]
                del _lock_access_count[p]
        return _locks[path]


def _path(key):
    h = hashlib.sha256(
        str(key).encode()
    ).hexdigest()[:32]
    return os.path.join(CACHE_DIR, f"{h}.json")


def cache_get(key):
    p = _path(key)
    if not os.path.exists(p):
        return None
    with _get_lock(p):
        try:
            with open(p, encoding="utf-8") as f:
                data = json.load(f)
            age = (
                time.time() - data.get("ts", 0)
            ) / 3600
            if age > CACHE_EXPIRY_HOURS:
                os.remove(p)
                return None
            return data.get("value")
        except Exception:
            try:
                os.remove(p)
            except OSError:
                pass
            return None


def cache_set(key, value):
    p = _path(key)
    with _get_lock(p):
        try:
            tmp = p + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(
                    {"ts": time.time(), "value": value},
                    f, ensure_ascii=False
                )
            os.replace(tmp, p)
        except Exception as e:
            print(f"[Cache] Write error: {e}")
            try:
                os.remove(p + ".tmp")
            except OSError:
                pass


def cache_clear():
    for fname in os.listdir(CACHE_DIR):
        if fname.endswith(".json"):
            try:
                os.remove(
                    os.path.join(CACHE_DIR, fname)
                )
            except OSError:
                pass
    with _lock_manager:
        _locks.clear()
        _lock_access_count.clear()