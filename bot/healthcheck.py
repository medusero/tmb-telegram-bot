import os

from telegram.ext import ContextTypes

from .tmb_api import obtener_llegadas


async def healthcheck(context: ContextTypes.DEFAULT_TYPE):
    telegram_user_id = int(os.environ["TELEGRAM_USER_ID"])
    contador = context.bot_data.get("fallos", 0)
    validador = context.bot_data.get("alerta", False)
    try:
        obtener_llegadas(1669)
        contador = 0
        context.bot_data["fallos"] = contador
    except Exception:
        contador += 1
        context.bot_data["fallos"] = contador
        if contador >= 3 and not validador:
            validador = True
            context.bot_data["alerta"] = validador
            await context.bot.send_message(chat_id=telegram_user_id, text="Revisa la API")
    else:
        if validador:
            validador = False
            context.bot_data["alerta"] = validador
            await context.bot.send_message(chat_id=telegram_user_id, text="API recuperada")
