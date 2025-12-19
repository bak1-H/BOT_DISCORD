# 🎵 Discord Music Bot

Bot de música para Discord que reproduce audio de YouTube, maneja colas por servidor y obtiene letras con Genius. Incluye comandos de moderación básicos y está listo para correr en Docker.

## ✨ Funcionalidades
- Reproducción en canales de voz con reconexión de streaming.
- Cola independiente por servidor y avance automático al terminar una canción.
- Búsqueda de letras en Genius con limpieza de títulos para mejores resultados.
- Limpieza de chat (`!clearchat`) con verificación de permisos.
- Comandos en español listos para uso: `!play`, `!skip`, `!stop`, `!cola`, `!lyrics`, etc.

## 🧰 Requisitos previos
- Python 3.11+
- FFmpeg instalado y disponible en la ruta del sistema (`ffmpeg -version` debe responder).
- Variables de entorno:
  - `DISCORD_TOKEN`: token del bot de Discord.
  - `GENIUS_TOKEN`: token de la API de Genius.

## 🚀 Instalación (local)
```bash
git clone <tu-repositorio>
cd DISCORD_BOT
python -m venv venv
venv\Scripts\activate  # En Linux/macOS: source venv/bin/activate
pip install -r requirements.txt
```

## ⚙️ Configuración
1) Crea un archivo `.env` en la raíz con:
```
DISCORD_TOKEN=tu_token_discord
GENIUS_TOKEN=tu_token_genius
```
2) Asegúrate de tener FFmpeg instalado. Ejemplos rápidos:
- Windows (Chocolatey): `choco install ffmpeg`
- Debian/Ubuntu: `sudo apt-get install ffmpeg`
- macOS (Homebrew): `brew install ffmpeg`

## ▶️ Ejecución
```bash
python bot.py
```
El bot se conecta y muestra en consola: `✅ Bot conectado como <nombre>`.

## 🎮 Comandos
| Comando | Descripción |
|---------|-------------|
| `!join` | Conecta el bot al canal de voz del usuario |
| `!play <nombre o URL>` | Reproduce o agrega a la cola (YouTube search incluido) |
| `!skip` | Salta la canción actual |
| `!stop` | Limpia la cola y desconecta del canal |
| `!cola` | Muestra la cola del servidor |
| `!clear` | Limpia por completo la cola |
| `!lyrics` | Obtiene la letra de la canción en reproducción |
| `!clearchat [cantidad]` | Elimina mensajes recientes (requiere gestionar mensajes) |
| `!comandos` | Muestra la lista de comandos |

## 🐳 Uso con Docker
Construir la imagen:
```bash
docker build -t discord-music-bot .
```

Ejecutar el contenedor:
```bash
docker run -d \
  --name discord-bot \
  -e DISCORD_TOKEN=tu_token \
  -e GENIUS_TOKEN=tu_token_genius \
  discord-music-bot
```

## 🔐 Permisos sugeridos en Discord
- Read Messages/View Channels, Send Messages, Read Message History.
- Manage Messages (solo si usarás `!clearchat`).
- Voice: Connect y Speak.

## 🗂️ Estructura
```
DISCORD_BOT/
├── bot.py           # Lógica del bot y comandos
├── requirements.txt # Dependencias
├── Dockerfile       # Imagen mínima con FFmpeg
└── README.md        # Documentación del proyecto
```

## 🧪 Tips y solución de problemas
- Si no suena audio: verifica FFmpeg (`ffmpeg -version`) y que el bot tenga permisos de voz.
- Si no busca letras: revisa `GENIUS_TOKEN` y que el título no sea genérico.
- El bot cierra la conexión de voz cuando la cola queda vacía; vuelve a usar `!play` para retomarlo.

## 📄 Licencia
MIT. Si reutilizas el código, se agradece atribución.
