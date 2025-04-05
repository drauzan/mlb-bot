import discord
import os
from dotenv import load_dotenv
from app.mlb_client import check_for_suspect_pitchers

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID"))

intents = discord.Intents.default()
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f"{client.user} is now running!")
    await check_for_suspect_pitchers(client, CHANNEL_ID)

def start_bot():
    client.run(TOKEN)
