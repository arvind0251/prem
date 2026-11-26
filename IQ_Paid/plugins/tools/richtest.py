"""/richtest - owner-only check for Telegram Rich Messages (Bot API 10.1 / 10.3).

Sends three sample cards so we can see what the Telegram app and the installed
library really support, before touching the real now-playing card:

  1. buttons only
  2. photo + title button + text + coloured buttons (reference layout)
  3. same as 2, with centred text

If the installed Kurigram has no rich-message API, the cards are sent through the
plain HTTP Bot API instead, so the test still works on Kurigram 2.2.19.
"""

import html as _html

import aiohttp
from pyrogram import enums, filters

from config import BOT_TOKEN, OWNER_ID
from IQ_Paid import LOGGER, app

try:  # Kurigram >= 2.2.2x
    from pyrogram.types import InputMediaPhoto, InputRichMessage, InputRichMessageMedia
except ImportError:  # older Kurigram: HTTP fallback below
    InputRichMessage = None

BOT_API_URL = "https://api.telegram.org"
THUMB = "https://i.ytimg.com/vi/jNQXAC9IVRw/hqdefault.jpg"
CB_PREFIX = "RICHTEST"


def _btn(text, *, data=None, url=None, style=None):
    kind = f'type="url" url="{_html.escape(url, quote=True)}"' if url else f'type="callback_data" data="{data}"'
    st = f' style="{style}"' if style else ""
    return f"<tg-button {kind}{st}>{_html.escape(text)}</tg-button>"


def _row(*buttons, align=None):
    al = f' align="{align}"' if align else ""
    return f"<tg-button-row{al}>{''.join(buttons)}</tg-button-row>"


def _buttons_html():
    return (
        _row(_btn("2:50 ———————————◉ 2:56", data=f"{CB_PREFIX}|progress", style="primary"))
        + _row(
            _btn("💥 Replay", data=f"{CB_PREFIX}|replay", style="success"),
            _btn("⏸ Pause", data=f"{CB_PREFIX}|pause", style="primary"),
            _btn("🕹 Skip", data=f"{CB_PREFIX}|skip", style="success"),
        )
        + _row(
            _btn("📝 Queue · 0", data=f"{CB_PREFIX}|queue", style="primary"),
            _btn("💎 Stop", data=f"{CB_PREFIX}|stop", style="danger"),
        )
    )


def _card_html(center: bool) -> str:
    p = '<p align="center">' if center else "<p>"
    return (
        '<img src="tg://photo?id=cover">'
        + _row(_btn("32 Ki Kamar Pe Chora Load 30 Ka Saman", url="https://t.me/l_Smoke_ll", style="danger"))
        + f"{p}ELEGANT SONG HARYANAVI</p>"
        + f"{p}<i>AUDIO · 2:56</i></p>"
        + f"{p}👤 Requested by Duggu</p>"
        + _buttons_html()
    )


def _basic_html() -> str:
    return "<p>Rich message test: buttons only</p>" + _buttons_html()


async def _send_native(chat_id, html, with_photo):
    media = None
    if with_photo:
        media = [InputRichMessageMedia(id="cover", media=InputMediaPhoto(media=THUMB))]
    await app.send_rich_message(chat_id, InputRichMessage(html=html, media=media))


async def _send_http(chat_id, html, with_photo):
    rich = {"html": html}
    if with_photo:
        rich["media"] = [{"id": "cover", "media": {"type": "photo", "media": THUMB}}]
    url = f"{BOT_API_URL}/bot{BOT_TOKEN}/sendRichMessage"
    async with aiohttp.ClientSession() as session:
        async with session.post(
            url, json={"chat_id": chat_id, "rich_message": rich}, timeout=aiohttp.ClientTimeout(total=30)
        ) as resp:
            data = await resp.json(content_type=None)
    if not data.get("ok"):
        raise RuntimeError(data.get("description", "unknown Bot API error"))


def _engine():
    if InputRichMessage is not None and hasattr(app, "send_rich_message"):
        return "native (Kurigram)", _send_native
    return "HTTP Bot API (library has no rich support)", _send_http


@app.on_message(filters.command("richtest") & filters.user(OWNER_ID))
async def richtest_cmd(_, message):
    name, send = _engine()
    tests = [
        ("1) buttons only", _basic_html(), False),
        ("2) photo + title button + text + buttons", _card_html(False), True),
        ("3) same, centred text", _card_html(True), True),
    ]
    report = [f"Rich message test, engine: {name}"]
    for title, html, with_photo in tests:
        try:
            await send(message.chat.id, html, with_photo)
            report.append(f"✅ {title}")
        except Exception as e:  # show the exact reason Telegram or the library gave
            reason = f"{type(e).__name__}: {e}"[:300]
            LOGGER(__name__).error(f"richtest '{title}' failed: {reason}")
            report.append(f"❌ {title}\n   {reason}")
    report.append("\nButtons dabake dekho. Agar kuch nahi hua, pm2 logs mein error check karo.")
    await message.reply_text("\n".join(report), parse_mode=enums.ParseMode.DISABLED)


@app.on_callback_query(filters.regex(rf"^{CB_PREFIX}"))
async def richtest_callback(_, query):
    await query.answer(f"✅ Callback mil gaya: {query.data}", show_alert=True)
