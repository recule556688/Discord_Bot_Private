"""Configuration and constants for the Discord bot."""

import os
from dotenv import load_dotenv

load_dotenv()

# Path to .env file (in app directory)
ENV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")

# Crafty API token (can be updated by authenticate)
_crafty_api_token = os.getenv("CRAFTY_API_TOKEN")


def get_crafty_api_token():
    global _crafty_api_token
    return _crafty_api_token


def set_crafty_api_token(token):
    global _crafty_api_token
    _crafty_api_token = token


# API keys (loaded from env when needed)
def get_api_weather():
    return os.getenv("OPENWEATHERMAP_API_KEY")


# Constants
CITY = [
    "New York",
    "Los Angeles",
    "Chicago",
    "San Francisco",
    "Paris",
    "Marseille",
    "Lyon",
    "Toulouse",
    "Nice",
    "Nantes",
    "Strasbourg",
    "Montpellier",
    "Bordeaux",
    "Lille",
    "Rennes",
    "Reims",
    "Saint-Étienne",
    "Toulon",
    "Angers",
    "Grenoble",
    "Dijon",
    "Aix-en-Provence",
    "Rive de Gier",
    "Saint-Chamond",
    "Villeurbanne",
]

ADDITIONAL_ALLOWED_USER_ID = (
    766746672964567052,
    287307876366548992,
)

WAITING_ROOM_SERVER_ID = 1321594106027184150
WAITING_ROOM_CHANNEL_ID = 1321594106639810612

BANNED_WORDS = [
    "roblox",
    "skibiki",
    "skibidi",
    "gay",
    "bebou",
    "quoicu",
    "noirs",
    "arabes",
    "NUPES",
    "skibi",
    "bi",
    "melenchon",
    "macron",
    "lfi",
    "trans",
    "transidentite",
    "fury",
    "furys",
    "asterion",
    "punisher",
    "immigre",
    "immigré",
    "immigrée",
    "immigrés",
    "immigrées",
    "immigration",
    "immigrante",
]
