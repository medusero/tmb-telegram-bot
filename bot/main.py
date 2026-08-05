import logging
import os

from dotenv import load_dotenv
from telegram import ForceReply, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from .tmb_api import obtener_llegadas

logging.basicConfig(level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)

load_dotenv()


telegram_bot_token = os.environ["TELEGRAM_BOT_TOKEN"]
telegram_user_id = int(os.environ["TELEGRAM_USER_ID"])
ESPERANDO_CODIGO = 1


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_html(
        rf"Hi {user.mention_html()}!",
        reply_markup=ForceReply(selective=True),
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Utiliza /parada <código> para obtener tiempos de llegada"
    )


def formatear_llegada(codi_parada):
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
    return texto


async def parada(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.effective_message.reply_text("Necesito un código de parada")
        return
    try:
        codi_parada = context.args[0]
        texto = formatear_llegada(codi_parada)
        await update.message.reply_text(texto)
    except Exception:
        await update.effective_message.reply_text(
            "La API no responde; inténtalo en unos minutos"
        )


async def llegadas_inicio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("¿Cual es el código de parada?")
    return ESPERANDO_CODIGO


async def llegadas_recibir(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        codi_parada = update.message.text
        texto = formatear_llegada(codi_parada)
        await update.message.reply_text(texto)
        return ConversationHandler.END
    except Exception:
        await update.effective_message.reply_text(
            "Eso no es un código de parada; inténtalo otra vez"
        )
        return ESPERANDO_CODIGO


async def post_init(application):
    await application.bot.set_my_commands(
        [
            ("start", "Inicia el bot"),
            ("help", "Recibe ayuda"),
            ("llegadas", "Consulta llegadas"),
        ]
    )


conv_handler = ConversationHandler(
    entry_points=[
        CommandHandler(
            "llegadas", llegadas_inicio, filters=filters.User(user_id=telegram_user_id)
        )
    ],
    states={
        ESPERANDO_CODIGO: [
            MessageHandler(
                filters.TEXT
                & ~filters.COMMAND
                & filters.User(user_id=telegram_user_id),
                llegadas_recibir,
            )
        ],
    },
    fallbacks=[],
)


def main():
    application = (
        Application.builder().token(telegram_bot_token).post_init(post_init).build()
    )
    application.add_handler(
        CommandHandler("start", start, filters=filters.User(user_id=telegram_user_id))
    )
    application.add_handler(
        CommandHandler(
            "help", help_command, filters=filters.User(user_id=telegram_user_id)
        )
    )
    application.add_handler(
        CommandHandler("parada", parada, filters=filters.User(user_id=telegram_user_id))
    )
    application.add_handler(conv_handler)
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
