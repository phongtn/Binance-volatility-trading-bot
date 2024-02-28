import telebot

from helpers.parameters import (
    load_config
)

notion_creds = load_config("creds.yml")
BOT_TOKEN = notion_creds['telegram']['bot_token']
CHAT_ID = notion_creds['telegram']['chat_id']
bot = telebot.TeleBot(BOT_TOKEN)


def send(message: str):
    bot.send_message(CHAT_ID, message)
