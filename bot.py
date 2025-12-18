import discord
from discord.ext import commands
import yt_dlp
import asyncio
import os
from dotenv import load_dotenv
import requests
import lyricsgenius
import re

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

genius = lyricsgenius.Genius(
    os.getenv("GENIUS_TOKEN"),
    skip_non_songs=True,
    excluded_terms=["(Remix)", "(Live)"],
    remove_section_headers=True
)


# Cola de canciones por servidor
queues = {}
current_song = {}


ytdlp_opts = {
    'format': 'bestaudio/best',
    'quiet': True,
    'noplaylist': True,
}

ffmpeg_opts = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn"
}
def get_queue(guild_id):
    if guild_id not in queues:
        queues[guild_id] = []
    return queues[guild_id]


async def play_next(ctx):
    queue = get_queue(ctx.guild.id)

    if not queue:
        await ctx.voice_client.disconnect()
        return

    url = queue.pop(0)

    with yt_dlp.YoutubeDL(ytdlp_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        audio_url = info['url']
        title = info['title']
        current_song[ctx.guild.id] = title


    ffmpeg_opts = {
        "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
        "options": "-vn"
    }

    source = discord.FFmpegPCMAudio(audio_url, **ffmpeg_opts)

    ctx.voice_client.play(
        source,
        after=lambda e: asyncio.run_coroutine_threadsafe(
            play_next(ctx), bot.loop
        )
    )

    await ctx.send(f"🎶 Reproduciendo: **{title}**")


@bot.event
async def on_ready():
    print(f"✅ Bot conectado como {bot.user}")


@bot.command()
async def join(ctx):
    if ctx.author.voice:
        channel = ctx.author.voice.channel
        await channel.connect()
        await ctx.send("🔊 Conectado al canal de voz")
    else:
        await ctx.send("❌ Debes estar en un canal de voz")


@bot.command()
async def play(ctx, *, search):
    if not ctx.author.voice:
        return await ctx.send("❌ Debes estar en un canal de voz")

    if not ctx.voice_client:
        await ctx.author.voice.channel.connect()

    # Buscar en YouTube
    with yt_dlp.YoutubeDL(ytdlp_opts) as ydl:
        info = ydl.extract_info(f"ytsearch:{search}", download=False)
        video = info['entries'][0]
        url = video['webpage_url']
        title = video['title']

    queue = get_queue(ctx.guild.id)
    queue.append(url)



    ## Se muestra al agregar la segunda cancion
    if len(queue) > 1:
        await ctx.send(f"➕ **{title}** ha sido añadida a la cola")

    if not ctx.voice_client.is_playing():
        await play_next(ctx)


@bot.command()
async def skip(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("⏭️ Canción saltada")


@bot.command()
async def stop(ctx):
    queue = get_queue(ctx.guild.id)
    queue.clear()

    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("⏹️ Música detenida y cola limpia")


@bot.command()
async def cola(ctx):
    queue = get_queue(ctx.guild.id)

    if not queue:
        return await ctx.send("📭 La cola está vacía")

    msg = "\n".join([f"{i+1}. {url}" for i, url in enumerate(queue)])
    await ctx.send(f"🎼 **Cola:**\n{msg}")

@bot.command()
async def clear(ctx):
    queue = get_queue(ctx.guild.id)
    queue.clear()
    await ctx.send("🗑️ Cola limpiada")

@bot.command()
@commands.has_permissions(manage_messages=True)
async def clearchat(ctx, limit: int = 100):
    """Elimina mensajes del chat. Requiere permisos de 'Gestionar mensajes'."""
    if not ctx.guild.me.guild_permissions.manage_messages:
        return await ctx.send("❌ No tengo permisos para gestionar mensajes")
    
    try:
        deleted = await ctx.channel.purge(limit=limit)
        await ctx.send(f"🗑️ {len(deleted)} mensajes eliminados", delete_after=5)
    except discord.Forbidden:
        await ctx.send("❌ No tengo permisos para eliminar mensajes en este canal")
    except discord.HTTPException as e:
        await ctx.send(f"❌ Error al eliminar mensajes: {e}")


@bot.event
async def on_command_error(ctx, error):
    """Manejo global de errores de comandos"""
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ No tienes permisos para usar este comando")
    elif isinstance(error, commands.CommandNotFound):
        pass  # Ignorar comandos no encontrados
    else:
        print(f"Error en comando {ctx.command}: {error}")


def clean_title_for_genius(title: str):
    original = title

    # Quitar contenido entre () y []
    title = re.sub(r"\(.*?\)", "", title)
    title = re.sub(r"\[.*?\]", "", title)

    # Quitar palabras comunes basura
    blacklist = [
        "official video", "official music video", "lyrics", "lyric video",
        "audio", "hd", "hq", "remastered", "explicit", "video",
        "4k", "visualizer"
    ]

    for word in blacklist:
        title = re.sub(word, "", title, flags=re.IGNORECASE)

    # Quitar ft / feat
    title = re.sub(r"ft\.?.*", "", title, flags=re.IGNORECASE)
    title = re.sub(r"feat\.?.*", "", title, flags=re.IGNORECASE)

    # Quitar emojis y símbolos raros
    title = re.sub(r"[^\w\s\-]", "", title)

    # Normalizar espacios
    title = re.sub(r"\s+", " ", title).strip()

    # Separar artista - canción
    if "-" in title:
        artist, song = title.split("-", 1)
        return artist.strip(), song.strip()

    # Fallback: no se pudo separar
    return None, title.strip()




@bot.command()
async def lyrics(ctx):
    title = current_song.get(ctx.guild.id)

    if not title:
        return await ctx.send("❌ No hay ninguna canción sonando")

    artist, song = clean_title_for_genius(title)

    try:
        if artist:
            song_data = genius.search_song(song, artist)
        else:
            song_data = genius.search_song(song)
    except Exception:
        return await ctx.send("❌ Error al buscar lyrics en Genius")

    if not song_data or not song_data.lyrics:
        return await ctx.send("❌ No se encontraron lyrics")

    lyrics = song_data.lyrics

    for i in range(0, len(lyrics), 1900):
        await ctx.send(f"```{lyrics[i:i+1900]}```")



@bot.command()
async def comandos(ctx):
    comandos_list = """
    🎵 **Comandos Disponibles:** 🎵
    `!join` - Conectar al canal de voz
    `!play <nombre o URL>` - Reproducir una canción o añadirla a la cola
    `!skip` - Saltar la canción actual
    `!stop` - Detener la música y desconectar
    `!cola` - Mostrar la cola de canciones
    `!clear` - Limpiar la cola de canciones
    `!clearchat [cantidad]` - Eliminar mensajes del chat
    `!lyrics` - Mostrar la letra de la canción actual

    `!comandos` - Mostrar esta lista de comandos
    """
    await ctx.send(comandos_list)





bot.run(os.getenv("DISCORD_TOKEN"))