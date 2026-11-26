import html
import re

from IQ_Paid import app
from IQ_Paid.button_styles import danger_button, primary_button, success_button
from IQ_Paid.misc import db
from IQ_Paid.utils.formatters import time_to_seconds
from IQ_Paid.utils.thumbnails import channel_cache

_BAR_LEN = 12


def _fmt(t):
    """02:56 -> 2:56, 01:02:03 -> 1:02:03 (matches the reference design)."""
    parts = str(t).split(":")
    if len(parts) in (2, 3) and all(x.isdigit() for x in parts):
        parts[0] = str(int(parts[0]))
        return ":".join(parts)
    return str(t)


def _bar(played, dur):
    try:
        total = time_to_seconds(dur)
        done = time_to_seconds(played)
        pct = (done / total) if total else 0
    except Exception:
        pct = 0
    idx = max(0, min(int(pct * _BAR_LEN), _BAR_LEN - 1))
    return "\u2014" * idx + "\u25c9" + "\u2014" * (_BAR_LEN - 1 - idx)


def np_markup(_, chat_id, played="00:00", dur=None, paused=False):
    """Now-playing keyboard: title link, progress, Replay/Pause/Skip, Queue/Stop."""
    queue = db.get(chat_id) or []
    entry = queue[0] if queue else {}
    dur = dur or entry.get("dur") or "00:00"
    vidid = str(entry.get("vidid") or "")
    title = entry.get("title")
    rows = []
    if title and len(vidid) == 11 and entry.get("streamtype") in ("audio", "video"):
        rows.append(
            [danger_button(text=str(title)[:40], url=f"https://t.me/{app.username}?start=info_{vidid}")]
        )
    rows.append([primary_button(text=f"{_fmt(played)} {_bar(played, dur)} {_fmt(dur)}", callback_data="GetTimer")])
    rows.append(
        [
            success_button(text="\U0001f4a5 Replay", callback_data=f"ADMIN Replay|{chat_id}"),
            primary_button(
                text="\u25b6\ufe0f Resume" if paused else "\u23f8 Pause",
                callback_data=f"ADMIN {'Resume' if paused else 'Pause'}|{chat_id}",
            ),
            success_button(text="\U0001f579 Skip", callback_data=f"ADMIN Skip|{chat_id}"),
        ]
    )
    rows.append(
        [
            primary_button(text=f"\U0001f4dd Queue \u00b7 {max(len(queue) - 1, 0)}", callback_data=f"NPQueue {chat_id}"),
            danger_button(text="\U0001f48e Stop", callback_data=f"ADMIN Stop|{chat_id}"),
        ]
    )
    return rows


def _kind_for(vid, extra):
    if vid:
        for q in list(db.values()):
            try:
                if q and q[0].get("vidid") == vid:
                    return "VIDEO" if q[0].get("streamtype") == "video" else "AUDIO"
            except Exception:
                pass
    if extra and "\U0001f3a5" in str(extra[0]):
        return "VIDEO"
    return "AUDIO"


def np_caption(_, link, title, duration, user, *extra):
    """Caption: CHANNEL / AUDIO · 2:56 / Requested by user. Same args as the old stream_1."""
    m = re.search(r"start=info_([A-Za-z0-9_-]{11})", str(link or ""))
    vid = m.group(1) if m else None
    header = html.escape(str(channel_cache.get(vid) or title)).upper() if vid or title else ""
    shown = f" \u00b7 {_fmt(duration)}" if duration and str(duration) not in ("0", "None", "Unknown") else ""
    return f"{header}\n<i>{_kind_for(vid, extra)}{shown}</i>\n\U0001f464 Requested by {user}"
