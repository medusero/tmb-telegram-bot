import os

from telegram.ext import ContextTypes

from .tmb_api import get_arrivals


async def healthcheck(context: ContextTypes.DEFAULT_TYPE):
    telegram_user_id = int(os.environ["TELEGRAM_USER_ID"])
    failure_count = context.bot_data.get("failures", 0)
    already_alerted = context.bot_data.get("alerted", False)
    try:
        get_arrivals(1669)
        failure_count = 0
        context.bot_data["failures"] = failure_count
    except Exception:
        failure_count += 1
        context.bot_data["failures"] = failure_count
        if failure_count >= 3 and not already_alerted:
            already_alerted = True
            context.bot_data["alerted"] = already_alerted
            await context.bot.send_message(chat_id=telegram_user_id, text="Revisa la API")
    else:
        if already_alerted:
            already_alerted = False
            context.bot_data["alerted"] = already_alerted
            await context.bot.send_message(chat_id=telegram_user_id, text="API recuperada")
