import requests
import logging
from datetime import datetime

logger = logging.getLogger("mlb-bot")

MLB_API_BASE = "https://statsapi.mlb.com/api/v1"

CURRENT_SEASON = datetime.now().year

def get_live_games():
    """Fetch live MLB games from the MLB API."""
    try:
        params = {"sportId": 1}
        response = requests.get(f"{MLB_API_BASE}/schedule", params=params)
        response.raise_for_status()
        data = response.json()

        games = []
        for date_info in data.get("dates", []):
            for game in date_info.get("games", []):
                if game.get("status", {}).get("abstractGameState") == "Live":
                    games.append({
                        "id": game["gamePk"],
                        "home": game["teams"]["home"]["team"]["name"],
                        "away": game["teams"]["away"]["team"]["name"],
                        "status": game["status"]["detailedState"],
                        "inning": game.get("linescore", {}).get("currentInning", 0)
                    })
        return games
    except Exception as e:
        logger.exception("Failed to fetch live games.")
        return []

def get_pitching_changes(game):
    """Fetch substitutions or pitching changes for a game."""
    try:
        game_id = game["id"]
        response = requests.get(f"{MLB_API_BASE}/game/{game_id}/boxscore")
        response.raise_for_status()
        data = response.json()

        subs = []

        for team_key in ["home", "away"]:
            players = data.get(team_key, {}).get("players", {})
            for player_id, player_data in players.items():
                stats = player_data.get("stats", {}).get("pitching", {})
                info = player_data.get("person", {})

                if stats and "inningsPitched" in stats:  # They’re currently pitching
                    sub = {
                        "incoming": {
                            "id": info.get("id"),
                            "fullName": info.get("fullName"),
                            "era": stats.get("era", 0),
                            "stolenBasePercentage": stats.get("stolenBasePercentage", 0),
                            "wildPitches": stats.get("wildPitches", 0),
                            "inheritedRunners": stats.get("inheritedRunners", 0),
                            "inheritedRunnersScored": stats.get("inheritedRunnersScored", 0),
                            "mlbDebutDate": info.get("mlbDebutDate")
                        }
                    }
                    subs.append(sub)
        return subs
    except Exception as e:
        logger.exception(f"Failed to get pitching changes for game {game['id']}")
        return []

def should_alert_for_pitcher(pitcher, game):
    """Determine if a pitching substitution should trigger an alert."""
    try:
        inning = game.get("inning", 0)
        if inning < 6:
            return False

        era = float(pitcher.get("era", 0) or 0)
        sb_pct = float(pitcher.get("stolenBasePercentage", 0) or 0)
        wild_pitches = int(pitcher.get("wildPitches", 0) or 0)
        inherited_scored = int(pitcher.get("inheritedRunnersScored", 0) or 0)
        debut_year = None

        if pitcher.get("mlbDebutDate"):
            debut_year = datetime.strptime(pitcher["mlbDebutDate"], "%Y-%m-%d").year

        return (
            era >= 5.00 or
            sb_pct >= 0.75 or
            wild_pitches >= 2 or
            inherited_scored >= 1 or
            debut_year == CURRENT_SEASON
        )
    except Exception as e:
        logger.exception("Error evaluating pitcher alert conditions.")
        return False
