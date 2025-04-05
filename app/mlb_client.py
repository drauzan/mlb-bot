import aiohttp
import asyncio
from datetime import datetime
import pytz

# Pitcher stat thresholds
ERA_THRESHOLD = 5.00
CURRENT_YEAR = 2025

# MLB API endpoints
LIVE_GAMES_URL = "https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={}"
LIVE_FEED_URL = "https://statsapi.mlb.com/api/v1.1/game/{}/feed/live"
PITCHER_STATS_URL = "https://statsapi.mlb.com/api/v1/people/{}?hydrate=stats(group=[pitching],type=[season])"

# Keep track of already-handled pitcher events to avoid repeats
seen_pitchers = set()


async def get_json(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            return await resp.json()


async def get_live_game_ids():
    today = datetime.now().strftime("%Y-%m-%d")
    data = await get_json(LIVE_GAMES_URL.format(today))
    games = data.get("dates", [])[0].get("games", []) if data.get("dates") else []
    return [game["gamePk"] for game in games if game["status"]["detailedState"] in ("In Progress", "Live")]


async def get_new_pitchers(game_id):
    feed = await get_json(LIVE_FEED_URL.format(game_id))
    all_plays = feed.get("liveData", {}).get("plays", {}).get("allPlays", [])
    new_pitchers = []

    for play in all_plays:
        event_type = play.get("result", {}).get("eventType", "")
        about = play.get("about", {})
        inning = about.get("inning", 0)

        if event_type == "pitchingSubstitution" and inning >= 6:
            pitcher = play.get("players", {}).get("pitcher", {}).get("id")
            if pitcher and pitcher not in seen_pitchers:
                new_pitchers.append((pitcher, inning))

    return new_pitchers


async def get_pitcher_stats(pitcher_id):
    data = await get_json(PITCHER_STATS_URL.format(pitcher_id))
    person = data.get("people", [])[0]

    # Basic info
    full_name = person.get("fullName", "Unknown")
    mlb_debut = person.get("mlbDebutDate", "1900-01-01")
    debut_year = int(mlb_debut.split("-")[0])

    # Stats
    pitching_stats = person.get("stats", [])
    era = None
    wild_pitches = 0
    stolen_base_pct = None
    inherited_runners_scored = None

    for stat_group in pitching_stats:
        if stat_group.get("type", {}).get("displayName") == "statsSingleSeason":
            stats = stat_group.get("splits", [{}])[0].get("stat", {})
            era = float(stats.get("era", 0))
            wild_pitches = int(stats.get("wildPitches", 0))
            stolen_base_pct = float(stats.get("stolenBasePercentage", 0))
            inherited_runners_scored = int(stats.get("inheritedRunnersScored", 0))

    return {
        "id": pitcher_id,
        "name": full_name,
        "debut_year": debut_year,
        "era": era,
        "wild_pitches": wild_pitches,
        "stolen_base_pct": stolen_base_pct,
        "inherited_runners_scored": inherited_runners_scored
    }


def pitcher_is_suspect(stats):
    return (
        stats["debut_year"] == CURRENT_YEAR and (
            stats["era"] and stats["era"] > ERA_THRESHOLD or
            stats["stolen_base_pct"] and stats["stolen_base_pct"] > 80 or
            stats["inherited_runners_scored"] and stats["inherited_runners_scored"] >= 5 or
            stats["wild_pitches"] and stats["wild_pitches"] > 3
        )
    )


async def check_for_suspect_pitchers(discord_client, channel_id):
    await discord_client.wait_until_ready()
    channel = discord_client.get_channel(channel_id)

    while True:
        try:
            game_ids = await get_live_game_ids()

            for game_id in game_ids:
                new_pitchers = await get_new_pitchers(game_id)

                for pitcher_id, inning in new_pitchers:
                    stats = await get_pitcher_stats(pitcher_id)

                    if pitcher_is_suspect(stats):
                        seen_pitchers.add(pitcher_id)
                        message = (
                            f"⚾ **Alert**: Suspect pitcher subbed in during the {inning}th inning!\n"
                            f"👤 Name: {stats['name']}\n"
                            f"📅 Debut Year: {stats['debut_year']}\n"
                            f"📉 ERA: {stats['era']}\n"
                            f"🎯 SB%: {stats['stolen_base_pct']}%\n"
                            f"🔥 Wild Pitches: {stats['wild_pitches']}\n"
                            f"👣 Inherited Runners Scored: {stats['inherited_runners_scored']}"
                        )
                        await channel.send(message)

        except Exception as e:
            print(f"Error in polling loop: {e}")

        await asyncio.sleep(30)
