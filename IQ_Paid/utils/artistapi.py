import asyncio
import logging
import time
from urllib.parse import urlencode

import requests

from config import ARTIST_API_URL, ARTIST_API_KEY, YT_API_KEY2, YTPROXY_URL2

logger = logging.getLogger(__name__)

_JSON_KEYS = ("stream", "stream_url", "url", "audio_url", "video_url", "download_url", "link")
_MEDIA_HINTS = ("audio/", "video/", "octet-stream", "mpegurl", "mp2t")


def _find_url(data):
    if isinstance(data, dict):
        for key in _JSON_KEYS:
            val = data.get(key)
            if isinstance(val, str) and val.startswith("http"):
                return val
        for val in data.values():
            if isinstance(val, dict):
                found = _find_url(val)
                if found:
                    return found
    return None


def _fetch(video_id: str, kind: str):
    if not (ARTIST_API_URL and ARTIST_API_KEY) or kind not in ("audio", "video"):
        return None
    params = {"url": video_id, "type": kind, "api_key": ARTIST_API_KEY}
    full_url = f"{ARTIST_API_URL.rstrip('/')}/stream?{urlencode(params)}"
    try:
        resp = requests.get(
            full_url,
            stream=True,
            timeout=20,
            allow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        try:
            if resp.status_code != 200:
                logger.error(f"ArtistBots {kind} HTTP {resp.status_code}: {video_id}")
                return None
            ctype = resp.headers.get("Content-Type", "").lower()
            if "json" in ctype:
                return _find_url(resp.json())
            if "html" in ctype:
                return None
            if any(h in ctype for h in _MEDIA_HINTS) or not ctype:
                return full_url
            return None
        finally:
            resp.close()
    except Exception as e:
        logger.error(f"ArtistBots {kind} failed: {type(e).__name__}")
        return None


async def get_artist_stream(video_id: str, kind: str = "audio"):
    """Playable stream URL from ArtistBots API, or None."""
    return await asyncio.to_thread(_fetch, video_id, kind)


def _fetch_babies(video_id: str):
    if not (YT_API_KEY2 and YTPROXY_URL2):
        return None
    try:
        resp = requests.get(
            f"{YTPROXY_URL2.rstrip('/')}/api/song",
            params={"query": video_id, "api": YT_API_KEY2},
            timeout=12,
        )
        if resp.status_code != 200:
            logger.error(f"BabiesIQ audio HTTP {resp.status_code}: {video_id}")
            return None
        stream = resp.json().get("stream")
        return stream if isinstance(stream, str) and stream.startswith("http") else None
    except Exception as e:
        logger.error(f"BabiesIQ audio failed: {type(e).__name__}")
        return None


async def get_fast_stream(video_id: str, kind: str = "audio", timeout: float = 15):
    """Ask every configured API at the same time; return the first working stream URL."""
    started = time.monotonic()
    pending = {asyncio.create_task(get_artist_stream(video_id, kind))}
    if kind == "audio":
        pending.add(asyncio.create_task(asyncio.to_thread(_fetch_babies, video_id)))
    result = None
    try:
        while pending and result is None:
            left = timeout - (time.monotonic() - started)
            if left <= 0:
                break
            done, pending = await asyncio.wait(pending, timeout=left, return_when=asyncio.FIRST_COMPLETED)
            if not done:
                break
            for task in done:
                try:
                    value = task.result()
                except Exception:
                    value = None
                if value:
                    result = value
                    break
    finally:
        for task in pending:
            task.cancel()
    if result:
        logger.info(f"Fast {kind} stream ready in {time.monotonic() - started:.1f}s: {video_id}")
    return result


def artist_download_url(video_id: str):
    """ArtistBots /download link (a real file, meant for saving). None if the API is not configured."""
    if not (ARTIST_API_URL and ARTIST_API_KEY):
        return None
    params = {"url": video_id, "type": "audio", "api_key": ARTIST_API_KEY}
    return f"{ARTIST_API_URL.rstrip('/')}/download?{urlencode(params)}"
