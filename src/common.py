"""Shared utilities: config, safe HTTP client (key never logged), storage budget, logging."""
from __future__ import annotations

import datetime as dt
import gzip
import json
import os
import random
import sys
import threading
import time
from pathlib import Path

import requests
import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config"
DATA = ROOT / "data"
RAW = DATA / "raw"
PARQ = DATA / "parquet"
MART = DATA / "mart"
STATE = ROOT / "state"
LOGS = ROOT / "logs"
OUT = ROOT / "output"
for p in (RAW, PARQ, MART, STATE, LOGS, OUT):
    p.mkdir(parents=True, exist_ok=True)

USER_AGENT = "grid-feasibility/0.1"
EIA_BASE = "https://api.eia.gov/v2"
HARD_STOP_BYTES = 10 * 1024 ** 3


def load_yaml(name: str) -> dict:
    with open(CONFIG / name, encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_api_key() -> str:
    key = os.environ.get("EIA_API_KEY")
    if not key and sys.platform == "win32":
        # user-level environment variable (HKCU\Environment) not yet inherited by this process
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
                key = winreg.QueryValueEx(k, "EIA_API_KEY")[0]
        except OSError:
            key = None
    if not key:
        raise SystemExit("EIA_API_KEY environment variable is not set")
    return key


_log_lock = threading.Lock()


def _scrub(text: str) -> str:
    try:
        key = get_api_key()
    except SystemExit:
        return text
    return str(text).replace(key, "***")


def log(msg: str, logfile: str = "pipeline.log") -> None:
    line = f"{dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')} {_scrub(msg)}"
    with _log_lock:
        print(line, flush=True)
        with open(LOGS / logfile, "a", encoding="utf-8") as f:
            f.write(line + "\n")


def dir_size(path: Path = ROOT) -> int:
    total = 0
    for dp, _, fns in os.walk(path):
        for fn in fns:
            try:
                total += os.path.getsize(os.path.join(dp, fn))
            except OSError:
                pass
    return total


class BudgetExceeded(RuntimeError):
    pass


_size_cache = {"t": 0.0, "v": 0}


def check_budget(force: bool = False) -> int:
    now = time.time()
    if force or now - _size_cache["t"] > 30:
        _size_cache["v"] = dir_size(ROOT)
        _size_cache["t"] = now
    if _size_cache["v"] > HARD_STOP_BYTES:
        raise BudgetExceeded(f"storage {_size_cache['v']} bytes > 10 GB hard stop")
    return _size_cache["v"]


# ---------------------------------------------------------------- HTTP
class RequestStats:
    def __init__(self):
        self.lock = threading.Lock()
        self.count = 0
        self.by_host: dict[str, int] = {}
        self.errors: list[str] = []

    def add(self, host: str):
        with self.lock:
            self.count += 1
            self.by_host[host] = self.by_host.get(host, 0) + 1


STATS = RequestStats()
_session = threading.local()


def session() -> requests.Session:
    if not hasattr(_session, "s"):
        s = requests.Session()
        s.headers["User-Agent"] = USER_AGENT
        _session.s = s
    return _session.s


def http_get(url: str, params: dict | None = None, *, eia: bool = False, max_tries: int = 8,
             timeout: int = 120, logfile: str = "http.log"):
    """GET with Retry-After + exponential backoff on 429/5xx. Returns (response, elapsed_s).
    The EIA key is added here and never written to logs (logged URL excludes params)."""
    params = dict(params or {})
    if eia:
        params["api_key"] = get_api_key()
    host = requests.utils.urlparse(url).netloc
    delay = 2.0
    last_exc = None
    for attempt in range(1, max_tries + 1):
        t0 = time.time()
        try:
            r = session().get(url, params=params, timeout=timeout)
            el = time.time() - t0
            STATS.add(host)
            if r.status_code == 429 or 500 <= r.status_code < 600:
                ra = r.headers.get("Retry-After")
                wait = None
                if ra:
                    try:
                        wait = float(ra)
                    except ValueError:
                        try:
                            wait = max(0.0, (dt.datetime.strptime(ra, "%a, %d %b %Y %H:%M:%S GMT")
                                             .replace(tzinfo=dt.timezone.utc)
                                             - dt.datetime.now(dt.timezone.utc)).total_seconds())
                        except ValueError:
                            wait = None
                if wait is None:
                    wait = delay + random.uniform(0, 1)
                    delay = min(delay * 2, 300)
                log(f"HTTP {r.status_code} {url} attempt {attempt}; sleep {wait:.1f}s", logfile)
                time.sleep(wait)
                continue
            return r, el
        except requests.RequestException as e:  # network
            last_exc = e
            log(f"NETERR {url} attempt {attempt}: {type(e).__name__}: {_scrub(str(e))[:300]}", logfile)
            time.sleep(delay + random.uniform(0, 1))
            delay = min(delay * 2, 300)
    raise RuntimeError(f"giving up on {url}: {_scrub(str(last_exc))[:300]}")


def write_json_gz(path: Path, obj) -> None:
    check_budget()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with gzip.open(tmp, "wt", encoding="utf-8") as f:
        json.dump(obj, f)
    os.replace(tmp, path)


def read_json_gz(path: Path):
    with gzip.open(path, "rt", encoding="utf-8") as f:
        return json.load(f)


def utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def run_state() -> dict:
    """D (run date UTC) is fixed at first run so reruns resume the same window."""
    p = STATE / "run_state.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    D = utcnow().date()
    st = {"D": D.isoformat(), "created_at": utcnow().isoformat(timespec="seconds"),
          "history_start": "2019-01-01T00",
          "history_end": (D - dt.timedelta(days=3)).isoformat() + "T23",
          "interchange_start": "2023-01-01T00"}
    p.write_text(json.dumps(st, indent=2), encoding="utf-8")
    return st


def save_json(name: str, obj) -> Path:
    p = OUT / name
    p.write_text(json.dumps(obj, indent=2, default=str, ensure_ascii=False), encoding="utf-8")
    return p


def load_json(name: str, default=None):
    p = OUT / name
    if not p.exists():
        return default
    return json.loads(p.read_text(encoding="utf-8"))

