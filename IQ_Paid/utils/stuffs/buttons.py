from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from pyrogram import Client, filters, enums 
from IQ_Paid.button_styles import primary_button
import config

class BUTTONS(object):
    ABUTTON = [
    [
        InlineKeyboardButton("sυᴘᴘᴏʀᴛ", url="https://t.me/l_Smoke_ll"),
        InlineKeyboardButton("υᴘᴅᴧᴛᴇs", url="https://t.me/l_Smoke_ll")
    ],
    [
        InlineKeyboardButton("ᴏᴡɴᴇʀ", user_id=config.OWNER_ID),
        primary_button(text="• ʙᴧᴄᴋ •", callback_data="settingsback_helper")
    ]
]

    INFO_BUTTON = [
    [
        primary_button(text="ʀєᴘσ", callback_data="gib_source"),
        primary_button(text="ʏᴛ-ᴀᴘɪ", callback_data="bot_info_data"),
        primary_button(text="ʟᴀɴɢᴜᴀɢᴇ", callback_data="LG"),
    ],
    [
        
        InlineKeyboardButton("ᴘʀɪᴠᴧᴄʏ", url="https://t.me/datacheak"),
        primary_button(text="• ʙᴧᴄᴋ •", callback_data="settingsback_helper"),
    ]
    ]
    


    INFO_NEW = [
    [
        primary_button(text="• ʙᴧᴄᴋ •", callback_data="settings_back_helper")],
    ]
