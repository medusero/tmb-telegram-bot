import logging
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from telegram import ForceReply, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from .favorites import (
    delete_favorites,
    list_favorites,
    load_favorites,
    save_favorites,
)
from .healthcheck import healthcheck
from .tmb_api import get_arrivals

logging.basicConfig(level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)

load_dotenv()


telegram_bot_token = os.environ["TELEGRAM_BOT_TOKEN"]
telegram_user_id = int(os.environ["TELEGRAM_USER_ID"])
WAITING_FOR_STOP_CODE = 1
WAITING_FOR_ALIAS = 2
WAITING_FOR_FAVORITE_CODE = 3


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_html(
        rf"Hola, {user.mention_html()}!",
        reply_markup=ForceReply(selective=True),
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    primer_encabezado = "*Usa los botones disponibles*:\n"
    primera_lista = "/llegadas\n/guardar\n/favoritos\n/cancelar\n"
    segundo_encabezado = "*O utiliza estos comandos directamente*:\n"
    segunda_lista = "/parada _código_: para obtener tiempos de llegada"
    await update.message.reply_markdown_v2(
        primer_encabezado + primera_lista + segundo_encabezado + segunda_lista
    )


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Operación cancelada.")
    return ConversationHandler.END


def format_arrivals(stop_code):
    h1 = datetime.now(ZoneInfo("Europe/Madrid"))
    arrivals = get_arrivals(stop_code)
    message_lines = []
    for i in arrivals:
        line_name = i["line_name"]
        arrival_times = i["arrival_times"]
        arrival_time_strings = []
        relative_times = []
        for k in arrival_times:
            arrival_time_str = k.strftime("%H:%M")
            arrival_time_strings.append(arrival_time_str)
            h2 = k
            delta = timedelta.total_seconds(h2 - h1)
            minutes_str = str(round(delta / 60))
            minutes_label = " (" + minutes_str + "m.)"
            relative_times.append(minutes_label)
        zipped = zip(arrival_time_strings, relative_times)
        formatted_arrivals = []
        for z1, z2 in zipped:
            combine = z1 + z2
            formatted_arrivals.append(combine)
        line_text = f"Linea {line_name}: {', '.join(formatted_arrivals)}"
        message_lines.append(line_text)
    text = f"\n".join(message_lines)
    return text


async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.effective_message.reply_text("Necesito un código de parada")
        return
    try:
        stop_code = context.args[0]
        text = format_arrivals(stop_code)
        await update.message.reply_text(text)
    except Exception:
        await update.effective_message.reply_text(
            "La API no responde; inténtalo en unos minutos"
        )


async def arrivals_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("¿Cuál es el código de parada?")
    return WAITING_FOR_STOP_CODE


async def arrivals_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        stop_code = update.message.text
        text = format_arrivals(stop_code)
        await update.message.reply_text(text)
        return ConversationHandler.END
    except Exception:
        await update.effective_message.reply_text(
            "Eso no es un código de parada; inténtalo otra vez"
        )
        return WAITING_FOR_STOP_CODE


async def favorites_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("¿Qué alias tendrá esta parada?")
    return WAITING_FOR_ALIAS


async def favorites_receive_alias(update: Update, context: ContextTypes.DEFAULT_TYPE):
    alias = update.message.text
    context.user_data["alias"] = alias
    await update.message.reply_text("¿Cuál es el código de parada?")
    return WAITING_FOR_FAVORITE_CODE
    return WAITING_FOR_ALIAS


async def favorites_receive_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    code = update.message.text
    try:
        int(code)
        favorites = load_favorites()
        alias = context.user_data["alias"]
        favorites[alias] = code
        save_favorites(favorites)
        await update.message.reply_text("Añadido el nuevo favorito")
        return ConversationHandler.END
    except Exception:
        await update.effective_message.reply_text(
            "El código de parada ha de ser un número"
        )
        return WAITING_FOR_FAVORITE_CODE


async def favorites_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    favorites = list_favorites()
    if not favorites:
        await update.message.reply_text("No tienes nada guardado")
    else:
        await update.message.reply_text(favorites)


async def favorites_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = []
    favorite_list = load_favorites()
    for index, (key, value) in enumerate(favorite_list.items()):
        button = InlineKeyboardButton(text=key + ": " + value, callback_data=str(index))
        keyboard.append([button])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Elige:", reply_markup=reply_markup)


async def delete_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id == telegram_user_id:
        query = update.callback_query
        int_query = int(query.data)
        favorite_lists = load_favorites()
        keys = list(favorite_lists.keys())
        await query.answer()
        await query.edit_message_text(
            text=f"Borrada la parada nº {delete_favorites(keys[int_query])}"
        )
    else:
        return


async def post_init(application):
    await application.bot.set_my_commands(
        [
            ("llegadas", "Consulta llegadas"),
            ("guardar", "Guarda tus paradas"),
            ("favoritos", "Lista tus paradas guardadas"),
            ("borrar", "Borra un favorito"),
            ("cancelar", "Cancela la operación"),
            ("start", "Inicia el bot"),
            ("help", "Recibe ayuda"),
        ]
    )


conv_handler = ConversationHandler(
    entry_points=[
        CommandHandler(
            "llegadas", arrivals_start, filters=filters.User(user_id=telegram_user_id)
        ),
    ],
    states={
        WAITING_FOR_STOP_CODE: [
            MessageHandler(
                filters.TEXT
                & ~filters.COMMAND
                & filters.User(user_id=telegram_user_id),
                arrivals_receive,
            )
        ],
    },
    fallbacks=[CommandHandler("cancelar", cancel)],
)

fav_handler = ConversationHandler(
    entry_points=[
        CommandHandler(
            "guardar", favorites_start, filters=filters.User(user_id=telegram_user_id)
        ),
    ],
    states={
        WAITING_FOR_ALIAS: [
            MessageHandler(
                filters.TEXT
                & ~filters.COMMAND
                & filters.User(user_id=telegram_user_id),
                favorites_receive_alias,
            )
        ],
        WAITING_FOR_FAVORITE_CODE: [
            MessageHandler(
                filters.TEXT
                & ~filters.COMMAND
                & filters.User(user_id=telegram_user_id),
                favorites_receive_code,
            )
        ],
    },
    fallbacks=[CommandHandler("cancelar", cancel)],
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
        CommandHandler(
            "cancelar", cancel, filters=filters.User(user_id=telegram_user_id)
        )
    )
    application.add_handler(
        CommandHandler(
            "parada", stop_command, filters=filters.User(user_id=telegram_user_id)
        )
    )
    application.add_handler(
        CommandHandler(
            "favoritos",
            favorites_list,
            filters=filters.User(user_id=telegram_user_id),
        )
    )
    application.add_handler(
        CommandHandler(
            "borrar",
            favorites_delete,
            filters=filters.User(user_id=telegram_user_id),
        )
    )
    application.add_handler(CallbackQueryHandler(delete_button))
    application.add_handler(conv_handler)
    application.add_handler(fav_handler)
    application.job_queue.run_repeating(healthcheck, interval=300, first=300)
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
