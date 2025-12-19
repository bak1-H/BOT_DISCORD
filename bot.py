import discord
from discord.ext import commands
import yt_dlp
import asyncio
import os
from dotenv import load_dotenv
import lyricsgenius
import re
import functools

load_dotenv()

COOKIES_ENV = os.getenv("YTDLP_COOKIES")

if COOKIES_ENV:
    with open("cookies.txt", "w", encoding="utf-8") as f:
        f.write(COOKIES_ENV)

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# =========================
# GENIUS
# =========================
genius = lyricsgenius.Genius(
    os.getenv("GENIUS_TOKEN"),
    skip_non_songs=True,
    excluded_terms=["(Remix)", "(Live)"],
    remove_section_headers=True,
    timeout=15,
    retries=3
)

# =========================
# ESTADO
# =========================
queues = {}
current_song = {}

def get_queue(guild_id):
    return queues.setdefault(guild_id, [])

# =========================
# YT-DLP CONFIG (SEGURO)
# =========================
ytdlp_opts = {
    "format": "bestaudio/best",
    "noplaylist": True,
    "quiet": True,
    "default_search": "ytsearch1",
    "outtmpl": "%(id)s.%(ext)s",
    "cookies": "cookies.txt",
    "socket_timeout": 10,
    "extractor_args": {
        "youtube": {
            "player_client": ["android"],  # 🔑 CLAVE
            "skip": ["webpage"],
        }
    }
}

# =========================
# UTILIDADES
# =========================
async def ytdlp_extract(loop, query, download=True):
    return await loop.run_in_executor(
        None,
        functools.partial(
            lambda: yt_dlp.YoutubeDL(ytdlp_opts).extract_info(query, download=download)
        )
    )

# =========================
# PLAY NEXT (ESTABLE)
# =========================
async def play_next(ctx):
    queue = get_queue(ctx.guild.id)

    if not queue:
        await ctx.voice_client.disconnect()
        return

    url = queue.pop(0)
    loop = asyncio.get_event_loop()

    try:
        info = await ytdlp_extract(loop, url, download=True)
    except Exception as e:
        msg = str(e).lower()

        if "confirm your age" in msg or "age" in msg:
            await ctx.send("🔞 Canción bloqueada por restricción de edad, se omitió.")
        else:
            await ctx.send("❌ Error al reproducir, se omitió la canción.")

        return await play_next(ctx)

    if "entries" in info:
        info = info["entries"][0]

    title = info.get("title", "Desconocido")
    filename = yt_dlp.YoutubeDL(ytdlp_opts).prepare_filename(info)

    current_song[ctx.guild.id] = title

    source = discord.FFmpegPCMAudio(filename, options="-vn")

    def after_playing(error):
        try:
            os.remove(filename)
        except:
            pass
        asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop)

    ctx.voice_client.play(source, after=after_playing)
    await ctx.send(f"🎶 Reproduciendo: **{title}**")

# =========================
# EVENTOS
# =========================
@bot.event
async def on_ready():
    print(f"✅ Bot conectado como {bot.user}")

# =========================
# COMANDOS DE VOZ
# =========================
@bot.command()
async def join(ctx):
    if ctx.author.voice:
        await ctx.author.voice.channel.connect()
        await ctx.send("Conectado al canal de voz")
    else:
        await ctx.send("Debes estar en un canal de voz")

# =========================

@bot.command()
async def play(ctx, *, search: str = None):
    if not search:
        return await ctx.send("Debes escribir una canción")

    if "playlist" in search.lower() or "list=" in search:
        return await ctx.send("Playlists no soportadas")

    if not ctx.voice_client:
        await ctx.author.voice.channel.connect()

    loop = asyncio.get_event_loop()

    try:
        info = await ytdlp_extract(loop, f"ytsearch1:{search}", download=False)
    except Exception:
        return await ctx.send("❌ Error buscando la canción")

    if not info or "entries" not in info or not info["entries"]:
        return await ctx.send("No se encontraron resultados")

    video = info["entries"][0]
    url = video["webpage_url"]
    title = video.get("title", "Desconocido")

    queue = get_queue(ctx.guild.id)
    queue.append(url)

    if ctx.voice_client.is_playing():
        await ctx.send(f"**{title}** añadida a la cola")
    else:
        await ctx.send(f"🎶 Reproduciendo: **{title}**")
        await play_next(ctx)


# =========================


@bot.command()
async def skip(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("⏭ Canción saltada")

# =========================


@bot.command()
async def stop(ctx):
    get_queue(ctx.guild.id).clear()
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("⏹ Música detenida")

# =========================


@bot.command()
async def cola(ctx):
    queue = get_queue(ctx.guild.id)
    if not queue:
        return await ctx.send("📭 Cola vacía")
    msg = "\n".join(f"{i+1}. {q}" for i, q in enumerate(queue))
    await ctx.send(f"🎼 **Cola:**\n{msg}")


# =========================
# LIMPIAR CHAT DE MENSAJES EN GENERAL
# =========================
@bot.command()
async def clearchat(ctx, amount: int = 5):
    if ctx.author.guild_permissions.manage_messages:
        deleted = await ctx.channel.purge(limit=amount)
        await ctx.send(f"🧹 Borrados {len(deleted)} mensajes.", delete_after=5)
    else:
        await ctx.send("❌ No tienes permisos para borrar mensajes.")


@bot.command()
async def repo(ctx):
    await ctx.send("🔗 Repositorio del bot: https://github.com/bak1-H/BOT_DISCORD")


# =========================
# LYRICS
# =========================
def clean_title_for_genius(title: str):
    title = re.sub(r"\(.*?\)|\[.*?\]", "", title)
    title = re.sub(r"(official|lyrics|video|hd|hq|audio|remastered)", "", title, flags=re.I)
    title = re.sub(r"ft\.?.*|feat\.?.*", "", title, flags=re.I)
    title = re.sub(r"[^\w\s\-]", "", title)
    title = re.sub(r"\s+", " ", title).strip()

    if "-" in title:
        artist, song = title.split("-", 1)
        return artist.strip(), song.strip()

    return None, title

# =========================

@bot.command()
async def lyrics(ctx):
    title = current_song.get(ctx.guild.id)

    if not title:
        return await ctx.send("❌ No hay canción sonando")

    artist, song = clean_title_for_genius(title)

    await ctx.send(f"🔍 Buscando lyrics: **{artist or ''} {song}**")

    try:
        song_data = (
            genius.search_song(song, artist)
            if artist
            else genius.search_song(song)
        )
    except Exception as e:
        print("GENIUS ERROR:", e)
        return await ctx.send("❌ Error conectando con Genius")

    if not song_data:
        return await ctx.send("❌ Genius no encontró la canción")

    if not song_data.lyrics:
        return await ctx.send("❌ La canción no tiene lyrics disponibles")

    lyrics = song_data.lyrics

    for i in range(0, len(lyrics), 1900):
        await ctx.send(f"```{lyrics[i:i+1900]}```")


@bot.command()
async def comandos(ctx):
    comandos_lista = """
    **Comandos disponibles:**
    `!join` - Conectar al canal de voz
    `!play <canción>` - Reproducir una canción o añadir a la cola
    `!skip` - Saltar la canción actual
    `!stop` - Detener la música y desconectar
    `!cola` - Mostrar la cola de canciones
    `!clearchat <n>` - Borrar los últimos n mensajes (por defecto 5)
    `!repo` - Mostrar el enlace al repositorio del bot  
    `!lyrics` - Obtener las letras de la canción actual
    `!comandos` - Mostrar esta lista de comandos
    """
    await ctx.send(comandos_lista)


# =========================
# ERRORES
# =========================
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    await ctx.send(f"Error: {error}")




bot.run(os.getenv("DISCORD_TOKEN"))
