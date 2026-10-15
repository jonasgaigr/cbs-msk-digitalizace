"""Shared helpers: polite HTTP session with retries, caching and paths."""
from __future__ import annotations

import csv
import hashlib
import time
import unicodedata
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urlunsplit

import requests

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "cache"
PDF_DIR = ROOT / "pdf"
MD_DIR = ROOT / "md"

USER_AGENT = "ZMSP-harvest/1.0 (botanical literature digitisation; python-requests)"
MIN_DELAY = 2.0  # seconds between requests to the same host
RETRIES = 3

_session = requests.Session()
_session.headers["User-Agent"] = USER_AGENT
_last_request: dict[str, float] = {}


def normalise_url(url: str, base: str | None = None) -> str:
    """Resolve relative URLs and force https for ms-cbs.cz / zenodo.org."""
    if base:
        url = urljoin(base, url)
    parts = urlsplit(url.strip())
    scheme = "https" if parts.scheme in ("http", "https") else parts.scheme
    return urlunsplit((scheme, parts.netloc, parts.path, parts.query, parts.fragment))


def _wait(host: str) -> None:
    last = _last_request.get(host)
    if last is not None:
        remaining = MIN_DELAY - (time.monotonic() - last)
        if remaining > 0:
            time.sleep(remaining)
    _last_request[host] = time.monotonic()


def get(url: str, *, stream: bool = False, params: dict | None = None) -> requests.Response:
    """GET with per-host delay and up to RETRIES attempts (backoff 5, 10, 20 s)."""
    host = urlsplit(url).netloc
    err: Exception | None = None
    for attempt in range(RETRIES):
        _wait(host)
        try:
            r = _session.get(url, params=params, timeout=60, stream=stream)
            if r.status_code == 429 or r.status_code >= 500:
                raise requests.HTTPError(f"HTTP {r.status_code}", response=r)
            return r
        except requests.RequestException as e:
            err = e
            time.sleep(5 * 2**attempt)
    raise RuntimeError(f"GET failed after {RETRIES} attempts: {url}: {err}")


def cached_text(url: str, refresh: bool = False) -> str:
    """Fetch a page once and keep it under cache/html/ (keyed by URL hash)."""
    path = CACHE / "html" / (hashlib.sha1(url.encode()).hexdigest()[:16] + ".html")
    if path.exists() and not refresh:
        return path.read_text(encoding="utf-8")
    r = get(url)
    r.raise_for_status()
    r.encoding = r.encoding if r.encoding and r.encoding.lower() != "iso-8859-1" else "utf-8"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(r.text, encoding="utf-8")
    return r.text


def download(url: str, dest: Path) -> tuple[str, str]:
    """Download to dest unless it exists. Returns (status, sha256)."""
    if dest.exists() and dest.stat().st_size > 0:
        return "exists", sha256(dest)
    r = get(url, stream=True)
    if r.status_code != 200:
        return f"http_{r.status_code}", ""
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    with open(tmp, "wb") as f:
        for chunk in r.iter_content(1 << 16):
            f.write(chunk)
    tmp.replace(dest)
    return "downloaded", sha256(dest)


def _cp1250_safe(value: str) -> str:
    """Make text encodable in Windows-1250: typographic primes → ASCII, other accents stripped."""
    value = value.replace("′", "'").replace("″", '"').replace("…", "...")
    out = []
    for ch in value:
        try:
            ch.encode("cp1250")
            out.append(ch)
        except UnicodeEncodeError:
            base = unicodedata.normalize("NFKD", ch)[0]
            try:
                base.encode("cp1250")
                out.append(base)
            except UnicodeEncodeError:
                out.append("?")
    return "".join(out)


def write_csv(path: Path, rows: list[dict], columns: list[str]) -> None:
    """Write <name>.csv (UTF-8 with BOM, comma) and <name>_cp1250.csv (Windows-1250, semicolon)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    cp = path.with_name(path.stem + "_cp1250.csv")
    with open(cp, "w", encoding="cp1250", newline="") as f:
        w = csv.DictWriter(f, fieldnames=columns, delimiter=";", extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: _cp1250_safe(str(r.get(k, "") if r.get(k) is not None else "")) for k in columns})


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()
