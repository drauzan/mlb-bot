import discord
import logging
import asyncio
from utils import should_alert_for_pitcher, get_live_games, get_pitching_changes

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("mlb-bot")

DISCORD_TOKEN = "your-discord-bot-token"
DISCORD_CHANNEL_ID = 123456789012345678  # Replace with your actual channel ID

class MLBDiscordBot(discord.Client):
    def __init__(self, *, intents: discord.Intents):
        super().__init__(intents=intents)

    async def on_ready(self):
        logger.debug(f"Logged in as {self.user} (ID: {self.user.id})")
        logger.debug("Bot is ready and watching for pitcher changes.")
        asyncio.create_task(self.monitor_pitching_changes())

    async def monitor_pitching_changes(self):
        logger.debug("Starting pitching change monitor loop.")
        seen_subs = set()

        while True:
            try:
                games = get_live_games()
                for game in games:
                    subs = get_pitching_changes(game)
                    for sub in subs:
                        sub_id = f"{game['id']}-{sub['incoming']['id']}"
                        if sub_id in seen_subs:
                            continue

                        if should_alert_for_pitcher(sub['incoming'], game):
                            logger.debug(f"Alert criteria met for {sub['incoming']['fullName']}")

                            channel = self.get_channel(DISCORD_CHANNEL_ID)
                            if channel:
                                await channel.send(
                                    f"🚨 *Suspicious substitution alert!* 🚨\n"
                                    f"**{game['home']} vs {game['away']}**\n"
                                    f"New pitcher: **{sub['incoming']['fullName']}**\n"
                                    f"ERA: {sub['incoming'].get('era', 'N/A')} | "
                                    f"SB%: {sub['incoming'].get('stolenBasePercentage', 'N/A')}\n"
                                    f"Game: {game['status']} — Inning: {game['inning']}"
                                )
                                seen_subs.add(sub_id)
                            else:
                                logger.error("Discord channel not found!")
            except Exception as e:
                logger.exception(f"Error while checking for pitcher changes: {e}")

            await asyncio.sleep(30)  # Poll interval

if __name__ == "__main__":
    intents = discord.Intents.default()
    client = MLBDiscordBot(intents=intents)
    client.run(DISCORD_TOKEN)
