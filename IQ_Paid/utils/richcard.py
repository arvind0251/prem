"""Now-playing card as a Telegram Rich Message (Bot API 10.1 / 10.3).

Photo, title button, text and all control buttons live inside ONE message.
Turn it on with RICH_CARD=1 in .env. When it is off (default), or when anything
goes wrong while sending, the normal photo card is used instead.

The card is sent and edited through the plain HTTP Bot API, so it works with the
installed Kurigram too. The object returned by send_np_card() mimics the parts of
a pyrogram Message the bot uses (id, chat, edit_reply_markup, edit_text, delete).
"""

import html as _html
import logging
import re
from types import SimpleNamespace

import aiohttp

from config import BOT_TOKEN, RICH_CARD

log = logging.getLogger("IQ_Paid.richcard")

RICH_ENABLED = bool(RICH_CARD)
BOT_API_URL = "https://api.telegram.org"
_STYLE_NAMES = {"PRIMARY": "primary", "SUCCESS": "success", "DANGER": "danger"}
_session = None


class RichCardError(Exception):
    pass


def _button_html(btn):
    text = _html.escape(str(btn.text))
    style = getattr(getattr(btn, "style", None), "name", "") or ""
    style = _STYLE_NAMES.get(str(style).split(".")[-1].upper())
    st = f' style="{style}"' if style else ""
    url = getattr(btn, "url", None)
    if url:
        return f'<tg-button type="url" url="{_html.escape(str(url), quote=True)}"{st}>{text}</tg-button>'
    data = getattr(btn, "callback_data", None)
    if isinstance(data, bytes):
        data = data.decode("utf-8", "ignore")
    if data is not None:
        return f'<tg-button type="callback_data" data="{_html.escape(str(data), quote=True)}"{st}>{text}</tg-button>'
    return ""


def markup_html(markup):
    rows = getattr(markup, "inline_keyboard", None) or []
    out = []
    for row in rows:
        cells = "".join(_button_html(b) for b in row)
        if cells:
            out.append(f"<tg-button-row>{cells}</tg-button-row>")
    return "".join(out)


def caption_html(caption):
    text = re.sub(r"href=([^\s\">]+)", r'href="\1"', str(caption or ""))
    return "".join(f'<p align="center">{line}</p>' for line in text.split("\n") if line.strip())


def build_rich(photo, caption, markup):
    return {
        "html": '<img src="tg://photo?id=cover">' + caption_html(caption) + markup_html(markup),
        "media": [{"id": "cover", "media": {"type": "photo", "media": photo}}],
    }


async def _call(method, payload):
    global _session
    if _session is None or _session.closed:
        _session = aiohttp.ClientSession()
    async with _session.post(
        f"{BOT_API_URL}/bot{BOT_TOKEN}/{method}", json=payload, timeout=aiohttp.ClientTimeout(total=20)
    ) as resp:
        data = await resp.json(content_type=None)
    if not data.get("ok"):
        raise RichCardError(data.get("description", "unknown Bot API error"))
    return data.get("result")


class RichCard:
    """Stands in for the pyrogram Message of the now-playing card."""

    def __init__(self, chat_id, message_id, photo, caption, markup, rich):
        self.chat = SimpleNamespace(id=chat_id)
        self.id = message_id
        self.message_id = message_id
        self._photo = photo
        self._caption = caption
        self._markup = markup
        self._last = rich

    async def _push(self):
        rich = build_rich(self._photo, self._caption, self._markup)
        if rich == self._last:
            return self
        try:
            await _call(
                "editMessageText",
                {"chat_id": self.chat.id, "message_id": self.id, "rich_message": rich},
            )
        except RichCardError as e:
            if "not modified" not in str(e).lower():
                raise
        self._last = rich
        return self

    async def edit_reply_markup(self, reply_markup=None, **kw):
        self._markup = reply_markup
        return await self._push()

    async def edit_caption(self, caption, reply_markup=None, **kw):
        self._caption = caption
        self._markup = reply_markup
        return await self._push()

    async def edit_text(self, text, reply_markup=None, **kw):
        return await self.edit_caption(text, reply_markup=reply_markup)

    async def delete(self, *a, **kw):
        try:
            await _call("deleteMessage", {"chat_id": self.chat.id, "message_id": self.id})
            return True
        except Exception:
            return False


async def send_np_card(client, chat_id=None, photo=None, caption=None, reply_markup=None, reply_to=None, **kw):
    """Drop-in for client.send_photo(...) used by the now-playing card."""
    if RICH_ENABLED and reply_markup is not None and isinstance(photo, str) and photo.startswith(("http://", "https://")):
        try:
            rich = build_rich(photo, caption, reply_markup)
            result = await _call("sendRichMessage", {"chat_id": chat_id, "rich_message": rich})
            return RichCard(chat_id, result["message_id"], photo, caption, reply_markup, rich)
        except Exception as e:
            log.error(f"Rich card failed, sending the normal card: {type(e).__name__}: {str(e)[:200]}")
    if reply_to is not None:  # same as before: reply to the user's message
        return await reply_to.reply_photo(photo=photo, caption=caption, reply_markup=reply_markup, **kw)
    return await client.send_photo(chat_id=chat_id, photo=photo, caption=caption, reply_markup=reply_markup, **kw)
