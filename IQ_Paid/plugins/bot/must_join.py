from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from pyrogram.errors import ChatAdminRequired, UserNotParticipant, ChatWriteForbidden
from IQ_Paid import app
from config import MUST_JOIN as _MUST_JOIN

_RAW = (_MUST_JOIN or "").strip().replace("https://t.me/", "").lstrip("@")
if _RAW.lstrip("-").isdigit():
    MUST_JOIN = int(_RAW)
else:
    MUST_JOIN = _RAW


@app.on_message(filters.incoming & filters.private, group=-1)
async def must_join_channel(app: Client, msg: Message):
    if not MUST_JOIN or not msg.from_user:
        return
    try:
        try:
            await app.get_chat_member(MUST_JOIN, msg.from_user.id)
        except UserNotParticipant:
            if isinstance(MUST_JOIN, str):
                link = "https://t.me/" + MUST_JOIN
            else:
                chat_info = await app.get_chat(MUST_JOIN)
                link = chat_info.invite_link
            try:
                await msg.reply_photo(
                    photo="https://files.catbox.moe/fu6jk3.jpg", caption=f"๏ ʏᴏᴜ ɴᴇᴇᴅ ᴛᴏ ᴊᴏɪɴ ᴛʜᴇ [๏ sᴜᴘᴘᴏʀᴛ ๏]({link}) ᴄʜᴀɴɴᴇʟ ᴛᴏ ᴄʜᴇᴀᴋ ᴍʏ ғᴇᴀᴛᴜʀᴇs.\n\nᴀғᴛᴇʀ ᴊᴏɪɴ ᴛʜᴇ [๏ ᴄʜᴀɴɴᴇʟ ๏]({link}) ᴄᴏᴍᴇ ʙᴀᴄᴋ ᴛᴏ ᴛʜᴇ ʙᴏᴛ ᴀɴᴅ ᴛʏᴘᴇ /start ᴀɢᴀɪɴ !! ",
                    reply_markup=InlineKeyboardMarkup(
                        [
                            [
                                InlineKeyboardButton("• ᴊᴏɪɴ •", url=link)],
                        ]
                    )
                )
                await msg.stop_propagation()
            except ChatWriteForbidden:
                pass
    except ChatAdminRequired:
        print(f"๏ ᴘʀᴏᴍᴏᴛᴇ ᴍᴇ ᴀs ᴀɴ ᴀᴅᴍɪɴ ɪɴ ᴛʜᴇ ᴍᴜsᴛ_ᴊᴏɪɴ ᴄʜᴀᴛ ๏: {MUST_JOIN} !")
    except Exception as e:
        print(f"MUST_JOIN check skipped: {type(e).__name__}")
