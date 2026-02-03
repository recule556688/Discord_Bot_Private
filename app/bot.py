"""Discord bot entry point."""

import asyncio
import logging
import os

import discord
from discord.ext import commands

from database import initialize_database
from cogs import COG_EXTENSIONS

# Setup logging
_log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
os.makedirs(_log_dir, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(_log_dir, "bot.log")),
        logging.StreamHandler(),
    ],
)

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    await bot.change_presence(
        activity=discord.Activity(
            name="Watching you in the shower",
            assets={
                "large_image": "aide",
                "large_text": "Watching something",
                "small_image": "aide",
                "small_text": "Watching something",
            },
        ),
        status=discord.Status.dnd,
    )

    bot.start_time = __import__("datetime").datetime.now()

    logging.info(f"Logged in as {bot.user.name} - {bot.user.id}")
    logging.info(f"{bot.user.name}_BOT is ready to go !")
    logging.info(f"Bot started at {bot.start_time}")

    try:
        synced = await bot.tree.sync()
        logging.info(f"Synced {len(synced)} commands")
    except Exception as e:
        logging.error(f"Failed to sync commands: {e}")


async def main():
    from dotenv import load_dotenv

    load_dotenv()

    # Crafty integration disabled - not in use
    # from config import set_crafty_api_token
    # from crafty_auth import authenticate
    # token = os.getenv("CRAFTY_API_TOKEN")
    # if token is None:
    #     await authenticate()
    # else:
    #     set_crafty_api_token(token)

    bot_token = os.getenv("BOT_TOKEN")
    api_weather = os.getenv("OPENWEATHERMAP_API_KEY")
    if bot_token is None or api_weather is None:
        logging.error(
            "Bot token or OPENWEATHERMAP_API_KEY is not set in the environment variables."
        )
        return

    # Load cogs
    for extension in COG_EXTENSIONS:
        try:
            await bot.load_extension(extension)
            logging.info(f"Loaded extension: {extension}")
        except Exception as e:
            logging.error(f"Failed to load extension {extension}: {e}")

    await bot.start(bot_token)


if __name__ == "__main__":
    try:
        initialize_database()
    except Exception as e:
        logging.error(f"Database connection failed: {e}")
        logging.error(
            "Ensure PostgreSQL is running. If using Docker: docker compose up db -d\n"
            "When running locally, set POSTGRES_HOST=localhost in .env"
        )
        raise

    asyncio.run(main())
    if os.path.exists("log_once_per_session.txt"):
        os.remove("log_once_per_session.txt")
