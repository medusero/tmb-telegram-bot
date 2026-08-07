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

from .favorites import (
    borrar_favoritos,
    cargar_favoritos,
    guardar_favoritos,
    listar_favoritos,
)
from .tmb_api import obtener_llegadas

logging.basicConfig(level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)

load_dotenv()


telegram_bot_token = os.environ["TELEGRAM_BOT_TOKEN"]
telegram_user_id = int(os.environ["TELEGRAM_USER_ID"])
ESPERANDO_CODIGO = 1
ESPERANDO_ALIAS = 2
ESPERANDO_CODIGO_FAV = 3


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_html(
        rf"Hi {user.mention_html()}!",
        reply_markup=ForceReply(selective=True),
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Usa los botones disponibles o utiliza /parada <código> para obtener tiempos de llegada directamente o /borrar <alias> para borrar un favorito")


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
        await update.effective_message.reply_text("La API no responde; inténtalo en unos minutos")


async def llegadas_inicio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("¿Cuál es el código de parada?")
    return ESPERANDO_CODIGO


async def llegadas_recibir(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        codi_parada = update.message.text
        texto = formatear_llegada(codi_parada)
        await update.message.reply_text(texto)
        return ConversationHandler.END
    except Exception:
        await update.effective_message.reply_text("Eso no es un código de parada; inténtalo otra vez")
        return ESPERANDO_CODIGO


async def favoritos_inicio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("¿Qué alias tendrá esta parada?")
    return ESPERANDO_ALIAS


async def favoritos_recibir_alias(update: Update, context: ContextTypes.DEFAULT_TYPE):
    alias = update.message.text
    if len(alias.split()) == 1:
        context.user_data["alias"] = alias
        await update.message.reply_text("¿Cuál es el código de parada?")
        return ESPERANDO_CODIGO_FAV
    else:
        await update.effective_message.reply_text("Has introducido dos palabras; solo se acepta una")
        return ESPERANDO_ALIAS


async def favoritos_recibir_codigo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    codigo = update.message.text
    try:
        int(codigo)
        favoritos = cargar_favoritos()
        alias = context.user_data["alias"]
        favoritos[alias] = codigo
        guardar_favoritos(favoritos)
        await update.message.reply_text("Añadido el nuevo favorito")
        return ConversationHandler.END
    except Exception:
        await update.effective_message.reply_text("El código de parada ha de ser un número")
        return ESPERANDO_CODIGO_FAV


async def favoritos_listar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    favoritos = listar_favoritos()
    if not favoritos:
        await update.message.reply_text("No tienes nada guardado")
    else:
        await update.message.reply_markdown(favoritos)


async def favoritos_borrar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.effective_message.reply_text("Necesito una entrada para borrar")
        return
    try:
        alias = context.args[0]
        borrar_favoritos(alias)
        await update.message.reply_text(f"{alias} ha sido borrado")
    except KeyError:
        await update.effective_message.reply_text(f"{alias} no está entre los guardados")


async def post_init(application):
    await application.bot.set_my_commands(
        [
            ("start", "Inicia el bot"),
            ("help", "Recibe ayuda"),
            ("llegadas", "Consulta llegadas"),
            ("guardar", "Guarda tus paradas"),
            ("favoritos", "Lista tus paradas guardadas"),
        ]
    )


conv_handler = ConversationHandler(
    entry_points=[
        CommandHandler(
            "llegadas", llegadas_inicio, filters=filters.User(user_id=telegram_user_id)
        ),
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

fav_handler = ConversationHandler(
    entry_points=[
        CommandHandler(
            "guardar", favoritos_inicio, filters=filters.User(user_id=telegram_user_id)
        ),
    ],
    states={
        ESPERANDO_ALIAS: [
            MessageHandler(
                filters.TEXT
                & ~filters.COMMAND
                & filters.User(user_id=telegram_user_id),
                favoritos_recibir_alias,
            )
        ],
        ESPERANDO_CODIGO_FAV: [
            MessageHandler(
                filters.TEXT
                & ~filters.COMMAND
                & filters.User(user_id=telegram_user_id),
                favoritos_recibir_codigo,
            )
        ],
    },
    fallbacks=[],
)


def main():
    application = (Application.builder().token(telegram_bot_token).post_init(post_init).build())
    application.add_handler(CommandHandler("start", start, filters=filters.User(user_id=telegram_user_id)))
    application.add_handler(CommandHandler("help", help_command, filters=filters.User(user_id=telegram_user_id)))
    application.add_handler(CommandHandler("parada", parada, filters=filters.User(user_id=telegram_user_id)))
    application.add_handler(CommandHandler("favoritos", favoritos_listar, filters=filters.User(user_id=telegram_user_id),))
    application.add_handler(CommandHandler("borrar", favoritos_borrar, filters=filters.User(user_id=telegram_user_id)))
    application.add_handler(conv_handler)
    application.add_handler(fav_handler)
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
