import discord
from discord.ext import commands
import yt_dlp
import asyncio
import os
from dotenv import load_dotenv
import requests
import lyricsgenius


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


@bot.command()
async def lyrics(ctx):
    title = current_song.get(ctx.guild.id)

    if not title:
        return await ctx.send("❌ No hay ninguna canción sonando")

    # Limpieza básica del título
    clean_title = title.replace("(Official Video)", "").replace("(Lyrics)", "").strip()

    try:
        song = genius.search_song(clean_title)
    except Exception as e:
        return await ctx.send("❌ Error al buscar la letra")

    if not song or not song.lyrics:
        return await ctx.send("❌ No se encontraron lyrics en Genius")

    lyrics = song.lyrics

    # Límite Discord 2000 chars
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
