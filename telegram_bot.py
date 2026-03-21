#!/usr/bin/env python3
"""
Telegram Bot for Brand Twin AI
Connects to the Brand Twin API and allows chatting via Telegram
"""
import os
import asyncio
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

load_dotenv('/agenticseek/.env')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_URL = os.getenv('TELEGRAM_API_URL', 'https://ii5nrun0ci2ahz-7777.proxy.runpod.net')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Ahoj! Som Tvojton AI bot. 🎉\n\n"
        "Môžem ti pomôcť s:\n"
        "• Chatom s AI\n"
        "• Generovaním obrázkov\n"
        "• Analýzou webstránok\n"
        "• A mnohým ďalším!\n\n"
        "Stačí mi napísať správu."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Pomoc:\n\n"
        "• Napíš mi otázku a odpoviem\n"
        "• 'Vygeneruj obrázok: [popis]' - vytvorím obrázok\n"
        "• 'Analyzuj: [URL]' - analyzujem webstránku\n"
        "• '/newchat' - začni nový rozhovor"
    )

async def newchat_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("Nový rozhovor začatý! 🎬")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    
    try:
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f'{API_URL}/query',
                json={'query': user_message},
                timeout=aiohttp.ClientTimeout(total=120)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    answer = data.get('answer', 'Odpoveď nie je dostupná.')
                    await update.message.reply_text(answer)
                else:
                    await update.message.reply_text("Nastala chyba pri komunikácii s AI.")
    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text(f"Nastala chyba: {str(e)[:200]}")

def main():
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not set!")
        logger.info("Get your bot token from @BotFather on Telegram")
        return
    
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("newchat", newchat_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("Telegram bot starting...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
