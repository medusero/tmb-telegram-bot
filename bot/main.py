import logging
import os
from datetime import datetime

from dotenv import load_dotenv
from telegram import ForceReply, Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)

from .tmb_api import obtener_llegadas

logging.basicConfig(level=logging.INFO)

load_dotenv()


telegram_bot_token = os.environ["TELEGRAM_BOT_TOKEN"]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_html(
        rf"Hi {user.mention_html()}!",
        reply_markup=ForceReply(selective=True),
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Help!")


async def parada(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.effective_message.reply_text("Necesito un código de parada")
        return
    codi_parada = context.args[0]
    lista = obtener_llegadas(codi_parada)
    mensaje = []
    for i in lista:
        nom_linia = i["linia"]
        horas = i["horas"]
        futures_arribades = []
        for k in horas:
            hora_arribada = k.strftime("%H:%M")
            futures_arribades.append(hora_arribada)
        linia_arribada = f"Linea {nom_linia}: {', '.join(futures_arribades)}"
        mensaje.append(linia_arribada)
    texto = f"\n".join(mensaje)
    await update.message.reply_text(texto)

async def post_init(application):
    await application.bot.set_my_commands([
        ("start", "Inicia el bot"),
        ("help", "Recibe ayuda"),
        ("parada", "Dale un código de parada")])


def main():
    application = Application.builder().token(telegram_bot_token).post_init(post_init).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("parada", parada))
    application.run_polling(allowed_updates=Update.ALL_TYPES)



if __name__ == "__main__":
    main()
