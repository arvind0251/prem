"""Keep played songs on the VPS so the next play starts instantly (no API call).

* Songs go to  songs/<video_id>.<ext>  (never touched by /restart or auto-clean).
* Saving runs in the background, so playback is not delayed.
* Total size is limited by SONG_CACHE_MB (0 = switch the feature off); the least
  recently played songs are deleted first.
"""

import asyncio
import logging
import os
import shutil
import time

import aiohttp

from config import SONG_CACHE_MB

log = logging.getLogger("IQ_Paid.songcache")

SONG_DIR = "songs"
MAX_BYTES = max(int(SONG_CACHE_MB or 0), 0) * 1024 * 1024
MIN_FILE = 50 * 1024  # smaller than this is an error page, not a song
MAX_FILE = 80 * 1024 * 1024  # skip very long videos
MIN_FREE = 1024 * 1024 * 1024  # keep at least 1 GB of disk free
_EXT = (
    ("mpeg", "mp3"), ("mp3", "mp3"), ("mp4", "m4a"), ("m4a", "m4a"), ("aac", "m4a"),
    ("webm", "webm"), ("ogg", "ogg"), ("opus", "ogg"), ("wav", "wav"), ("flac", "flac"),
)
_busy = set()
_tasks = set()


def enabled() -> bool:
    return MAX_BYTES > 0


def _ext_for(content_type: str) -> str:
    ct = (content_type or "").lower()
    for key, ext in _EXT:
        if key in ct:
            return ext
    return "mp3"


def cached_path(video_id: str):
    """Saved song for this video, or None. Playing it refreshes its 'last used' time."""
    if not enabled() or not os.path.isdir(SONG_DIR):
        return None
    prefix = f"{video_id}."
    for name in os.listdir(SONG_DIR):
        if name.startswith(prefix) and not name.endswith(".part"):
            path = os.path.join(SONG_DIR, name)
            if os.path.getsize(path) >= MIN_FILE:
                try:
                    os.utime(path, None)
                except OSError:
                    pass
                return path
    return None


def is_cache_path(path) -> bool:
    try:
        return os.path.abspath(str(path)).startswith(os.path.abspath(SONG_DIR) + os.sep)
    except Exception:
        return False


def _evict(keep: str = None):
    """Delete stale .part files, then the least recently played songs until we are under the limit."""
    try:
        files = []
        for name in os.listdir(SONG_DIR):
            path = os.path.join(SONG_DIR, name)
            if not os.path.isfile(path):
                continue
            if name.endswith(".part"):
                if time.time() - os.path.getmtime(path) > 3600:
                    os.remove(path)
                continue
            files.append((os.path.getmtime(path), os.path.getsize(path), path))
        total = sum(f[1] for f in files)
        if total <= MAX_BYTES:
            return
        for _, size, path in sorted(files):
            if total <= MAX_BYTES * 0.9:
                break
            if path == keep:
                continue
            os.remove(path)
            total -= size
    except Exception as e:
        log.error(f"song cache cleanup failed: {type(e).__name__}: {e}")


async def _download(session, url: str, part: str):
    async with session.get(url, timeout=aiohttp.ClientTimeout(total=180), allow_redirects=True) as resp:
        if resp.status != 200:
            raise RuntimeError(f"HTTP {resp.status}")
        ctype = resp.headers.get("Content-Type", "")
        low = ctype.lower()
        if "json" in low:
            data = await resp.json(content_type=None)
            nxt = None
            if isinstance(data, dict):
                for key in ("download", "download_url", "stream", "stream_url", "url", "audio_url", "link"):
                    val = data.get(key)
                    if isinstance(val, str) and val.startswith("http"):
                        nxt = val
                        break
            if not nxt:
                raise RuntimeError("JSON answer without a file link")
            return await _download(session, nxt, part)
        if "html" in low or "text/" in low:
            raise RuntimeError(f"not audio ({ctype})")
        size = 0
        with open(part, "wb") as fh:
            async for chunk in resp.content.iter_chunked(64 * 1024):
                size += len(chunk)
                if size > MAX_FILE:
                    raise RuntimeError("file too big")
                fh.write(chunk)
        if size < MIN_FILE:
            raise RuntimeError(f"file too small ({size} bytes)")
        return ctype, size


async def save_song(video_id: str, urls) -> None:
    """Download the song from the first working URL into songs/ (runs in the background)."""
    if not enabled() or video_id in _busy or cached_path(video_id):
        return
    _busy.add(video_id)
    part = os.path.join(SONG_DIR, f"{video_id}.part")
    try:
        os.makedirs(SONG_DIR, exist_ok=True)
        if shutil.disk_usage(SONG_DIR).free < MIN_FREE:
            log.error("song cache skipped: less than 1 GB of disk left")
            return
        async with aiohttp.ClientSession(headers={"User-Agent": "Mozilla/5.0"}) as session:
            for url in [u for u in urls if u]:
                try:
                    ctype, size = await _download(session, url, part)
                except Exception as e:
                    log.error(f"song save failed ({video_id}): {type(e).__name__}: {str(e)[:120]}")
                    if os.path.exists(part):
                        os.remove(part)
                    continue
                final = os.path.join(SONG_DIR, f"{video_id}.{_ext_for(ctype)}")
                os.replace(part, final)
                log.info(f"Saved song on VPS: {video_id} ({size / 1048576:.1f} MB)")
                _evict(keep=final)
                return
    except Exception as e:
        log.error(f"song save crashed ({video_id}): {type(e).__name__}: {e}")
    finally:
        _busy.discard(video_id)
        if os.path.exists(part):
            try:
                os.remove(part)
            except OSError:
                pass


def save_in_background(video_id: str, urls) -> None:
    """Start save_song() without waiting for it (the song keeps playing meanwhile)."""
    if not enabled():
        return
    task = asyncio.create_task(save_song(video_id, urls))
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)
