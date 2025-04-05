import discord
import aiohttp
import asyncio
import os

TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID"))
TEAM_ID = 133  # Athletics

client = discord.Client(intents=discord.Intents.default())
last_event = None

async def get_game_pk():
    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&teamId={TEAM_ID}&date=TODAY"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            data = await resp.json()
            try:
                return data["dates"][0]["games"][0]["gamePk"]
            except Exception:
                return None

async def check_pitching_changes(game_pk):
    global last_event
    url = f"https://statsapi.mlb.com/api/v1.1/game/{game_pk}/feed/live"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            data = await resp.json()
            plays = data["liveData"]["plays"]["allPlays"]
            for play in reversed(plays):
                desc = play["result"]["description"]
                if "Pitching Substitution" in desc:
                    if desc != last_event:
                        last_event = desc
                        return desc
    return None

async def poll_loop():
    await client.wait_until_ready()
    channel = client.get_channel(CHANNEL_ID)
    while not client.is_closed():
        game_pk = await get_game_pk()
        if game_pk:
            event = await check_pitching_changes(game_pk)
            if event:
                await channel.send(f"🧢 Pitching Change: {event}")
        await asyncio.sleep(60)

@client.event
async def on_ready():
    print(f"Logged in as {client.user}")
    client.loop.create_task(poll_loop())

client.run(TOKEN)
