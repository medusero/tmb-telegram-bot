# Sencillo bot de telegram para la API de TMB
Como el encabezado reza, es un simplísimo bot para recibir horarios de llegada de las paradas de Transports Metropolitans de Barcelona.  
Está pensado como bot personal, así que todos los handlers están protegidos con `filters.User(user_id=telegram_user_id)`.
## Descripción del bot
### bot/tmb_api.py: capa de acceso a la API de TMB.
***arrivals_receive(stop_code)***  
Hace la petición HTTP a GET /v1/itransit/bus/parades/{codi_parada} con app_id/app_key como query params.  
Si el status es 200:
- Recorre `linies_trajectes` → `propers_busos` de la respuesta JSON
- Convierte cada `temps_arribada` (epoch en milisegundos) a un datetime con zona horaria Europe/Madrid
- Devuelve una lista de diccionarios {"line_name": nombre, "arrival_times": [datetime, ...]}.

Si el status no es 200 lanza una excepción con el código incluido.
### bot/favorites.py: persistencia de favoritos en JSON.
***load_favorites()***  
Lee `data/favorites.json` (ruta anclada al propio módulo vía __file__, no al directorio de trabajo). Devuelve {} si el archivo no existe o está corrupto.  
***save_favorites(f)***  
Sobrescribe el archivo completo con el diccionario recibido.  
***list_favorites()***  
Reutiliza load_favorites() y devuelve un listado en texto plano ("- alias: código" por línea), o "" si no hay nada.  
***delete_favorites(f)***  
Carga, hace .pop(alias) (lanza KeyError si no existe) y vuelve a guardar.  
### bot/healthcheck.py: vigilancia proactiva de la API.
***healthcheck(context)***  
Se ejecuta periódicamente (cada 5 min, vía job_queue).  
Intenta obtener_llegadas con una parada fija; si falla 3 veces seguidas, avisa por Telegram ("Revisa la API"); cuando vuelve a funcionar tras haber avisado, notifica la recuperación.  
El estado (contador de fallos, si ya se avisó) vive en context.bot_data, un diccionario que persiste entre invocaciones del job mientras el proceso siga vivo.
### bot/main.py: comandos, conversaciones y formateo.
***format_arrivals(stop_code)***  
Toma la salida de obtener_llegadas y construye el texto final por línea, con hora absoluta y minutos relativos entre paréntesis (p. ej. 08:15 (6m.)).
### Comandos simples:
- `/start`
- `/help`
- `/cancelar`
- `/parada` "código"
- `/favoritos`
### Flujos conversacionales (ConversationHandler):
- `/llegadas` (pregunta el código de parada y luego responde)
- `/guardar` (pregunta alias y luego código, y lo guarda)
- `/cancelar` (salida de emergencia para los dos de arriba)
### Menú de botones:
- `/borrar` (presenta cada favorito como un botón; pulsar uno lo elimina)
### Otros detalles
- post_init: registra el menú al arrancar.
- main(): monta la Application, registra todos los handlers y el job de healthcheck, y arranca el polling.

## Requisitos previos
- Docker o Podman, según el modo de despliegue que prefieras.
- Una API de TMB: Se obtiene creando una cuenta (gratuita) en [developer.tmb.cat](https://developer.tmb.cat).
- Una cuenta (gratuita) de Telegram y crear un bot con [BotFather](https://telegram.me/BotFather).

El bot solo hace peticiones salientes (long polling a Telegram + llamadas a la API de TMB), así que no hace falta exponer ningún puerto.  
## Despliegue
### Docker
Clona el repositorio en local y construye la imagen.  
Copia el `.env.example` a tu directorio de trabajo. Para este ejemplo pongamos que es `$HOME/bot`.  
Rellena los datos del `.env` para `TMB_APP_ID`, `TMB_APP_KEY`, `TELEGRAM_BOT_TOKEN` y `TELEGRAM_USER_ID`.   
Crea el directorio de montaje, de lo contrario Docker la crearía como root en el despliegue, y el servicio (que corre con `uid 1000`) no podría escribir nada en él.
```
mkdir $HOME/bot
git clone https://github.com/medusero/tmb-telegram-bot.git
cd tmb-telegram-bot
docker build -t tmb-bot .
cp .env.example $HOME/bot/.env
cd $HOME/bot/
chmod 600 .env
mkdir data
```
#### Con el comando docker a pelo
Puesto que ya hemos construido la imagen previamente lo podemos lanzar sin build:
```
docker run -d --name tmb-bot --env-file .env -v ./data:/app/data --restart unless-stopped tmb-bot
```
#### Con Docker Compose
Crea el archivo `$HOME/bot/compose.yaml` con este contenido:
```yaml
services:
    tmb-bot:
        container_name: tmb-bot
        env_file:
            - .env
        volumes:
            - ./data:/app/data
        restart: unless-stopped
        image: tmb-bot
```
Desde el directorio `$HOME/bot`:
```
docker compose up -d
```
### Podman
Igual que con Docker, pero ojo si vas rootless: la imagen corre con `uid 1000` dentro del contenedor, y ese UID no mapea automáticamente al dueño del directorio del host, aunque este tambien sea `uid 1000`. Lo arreglamos con `podman unshare`. 
```
mkdir $HOME/bot
git clone https://github.com/medusero/tmb-telegram-bot.git
cd tmb-telegram-bot
podman build -t tmb-bot .
cp .env.example $HOME/bot/.env
cd $HOME/bot/
chmod 600 .env
mkdir data
podman unshare chown 1000:1000 data
```
#### Con el comando podman a pelo
```
podman run -d --name tmb-bot --env-file .env -v ./data:/app/data:Z --restart unless-stopped tmb-bot
```
#### Como quadlet bajo systemd
Crea el archivo `$HOME/.config/containers/systemd/tmb-bot.container` con este contenido:
```ini
[Container]
NoNewPrivileges=true
ContainerName=tmb-bot
Image=localhost/tmb-bot:latest
EnvironmentFile=%h/bot/.env
Environment=TZ=Europe/Madrid
DropCapability=all
Volume=%h/bot/data:/app/data:Z

[Service]
MemoryMax=128M

[Install]
WantedBy=default.target
```
Luego carga el demonio y lanza el servicio:
```
systemctl --user daemon-reload
systemctl --user start tmb-bot.service
```
