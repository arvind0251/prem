from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from IQ_Paid import app

@app.on_message(filters.command("privacy"))
async def privacy_command(client: Client, message: Message):
    await message.reply_photo(
        photo="https://files.catbox.moe/naban1.jpg",
        caption="**➻ ᴡᴇʟᴄᴏᴍᴇ ᴛᴏ ˹ʙᴏᴛѕ˼ ᴘʀɪᴠᴀᴄʏ ᴘᴏʟɪᴄʏ.**\n\n**⊚ ᴄʟɪᴄᴋ ᴛʜᴇ ʙᴇʟᴏᴡ ʙᴜᴛᴛᴏɴ ᴛʜᴇɴ ꜱᴇᴇ ᴘʀɪᴠᴀᴄʏ ᴘᴏʟɪᴄʏ 🔏**",
        reply_markup=InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("˹ ᴘʀɪᴠᴀᴄʏ ˼", url="https://t.me/datacheak")]
            ]
        )
    )
