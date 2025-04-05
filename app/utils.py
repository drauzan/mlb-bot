import os
import discord
from discord.ext import commands

def get_env_var(name: str, default: str = None):
    value = os.getenv(name)
    if not value and default is None:
        raise EnvironmentError(f"Missing required environment variable: {name}")
    return value or default


def create_discord_bot(on_ready_callback):
    intents = discord.Intents.default()
    intents.messages = True
    intents.guilds = True

    bot = commands.Bot(command_prefix="!", intents=intents)

    @bot.event
    async def on_ready():
        print(f"✅ Logged in as {bot.user.name}")
        await on_ready_callback(bot)

    return bot
