import json
import random
import re
import typing
import string
import discord
import os
import asyncio
import requests
import aiohttp
import logging
from discord import (
    Interaction,
    SelectOption,
    app_commands,
    Embed,
    ui,
    ButtonStyle,
    Colour,
)
from discord.ext import commands, tasks
from dotenv import load_dotenv
from datetime import datetime, timedelta
from dateutil.parser import parse
import psycopg2
from PIL import Image, ImageDraw, ImageFont, ImageSequence
import io

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("data/bot.log"),  # Log to file
        logging.StreamHandler(),  # Log to console
    ],
)


# Database connection function
def get_db_connection():
    conn = psycopg2.connect(
        dbname=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        host=os.getenv("POSTGRES_HOST"),
        port=os.getenv("POSTGRES_PORT"),
    )
    return conn


def initialize_database():
    conn = get_db_connection()
    cur = conn.cursor()

    # Create logging_channels table if it doesn't exist
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS logging_channels (
            id SERIAL PRIMARY KEY,
            channel_id BIGINT NOT NULL UNIQUE
        );
        """
    )

    # Create message_logs table if it doesn't exist
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS message_logs (
            id SERIAL PRIMARY KEY,
            encoded_message TEXT NOT NULL
        );
        """
    )

    # Create birthdays table with a unique constraint on the username column
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS birthdays (
            id SERIAL PRIMARY KEY,
            username VARCHAR(255) NOT NULL UNIQUE,
            birthdate DATE NOT NULL
        );
        """
    )

    conn.commit()
    cur.close()
    conn.close()


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

# Load .env file
load_dotenv()
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

# Create a global variable to store the user, message, and time
scheduled_message = {"user": None, "message": "", "time": ""}

ADDITIONAL_ALLOWED_USER_ID = (
    766746672964567052,
    287307876366548992,
)  # Allow the bot owner and the additional user to use the owner command


def is_owner():
    async def predicate(interaction: discord.Interaction):
        # Check if the user is the server owner
        is_server_owner = interaction.user.id == interaction.guild.owner_id
        # Check if the user is the additional allowed user
        is_additional_user = interaction.user.id in ADDITIONAL_ALLOWED_USER_ID
        # Allow if the user is either the server owner or the additional allowed user
        return is_server_owner or is_additional_user

    return app_commands.check(predicate)


@bot.tree.command(
    name="addrole",
    description="Assign yourself a specific role by its ID",
)
async def add_role_slash(interaction: discord.Interaction, role_id: discord.Role):
    member = interaction.user

    try:
        await member.add_roles(role_id)
        await interaction.response.send_message(
            f"Role {role_id.name} has been added to you!", ephemeral=True
        )
    except discord.Forbidden:
        await interaction.response.send_message(
            "I don't have permission to assign this role.", ephemeral=True
        )
    except discord.HTTPException:
        await interaction.response.send_message(
            "Failed to assign the role.", ephemeral=True
        )


@bot.tree.command(
    name="ping",
    description="Returns the bot's latency",
)
async def ping_slash(interaction: discord.Interaction):
    await interaction.response.send_message(
        f"Pong! {round(bot.latency * 1000)}ms", ephemeral=True
    )


@bot.tree.command(
    name="owner",
    description="This command is only for the owner of the server",
)
@is_owner()
async def owner_slash(interaction: discord.Interaction):
    await interaction.response.send_message(
        f"Hello, {interaction.user.mention} (:", ephemeral=True
    )


@tasks.loop(seconds=10)  # Check every 10 seconds
async def check_time():
    global scheduled_message
    if scheduled_message["user"] is not None:
        # Get the current date and time
        now = datetime.now()
        # Get the scheduled date and time
        scheduled_time = datetime.strptime(scheduled_message["time"], "%Y-%m-%d %Hh%M")
        # Check if the current date and time match or are later than the scheduled date and time
        if now >= scheduled_time:
            try:
                await scheduled_message["user"].send(scheduled_message["message"])
                logging.info(
                    f"Successfully sent message to {scheduled_message['user'].name}."
                )
                # Reset the scheduled message
                scheduled_message = {"user": None, "message": "", "time": ""}
            except discord.Forbidden:
                logging.error(
                    f"Failed to send a DM to {scheduled_message['user'].name}. They might have DMs disabled or the bot doesn't share a server with them."
                )


@bot.tree.command(
    name="dm",
    description="Send a DM to a user",
)
async def dm_slash(
    interaction: discord.Interaction,
    user: discord.User,
    times: int,
    message: str,
    time: str = None,
):
    if time is not None:
        if " " not in time:
            today = datetime.today().strftime("%Y-%m-%d")
            time = f"{today} {time}"
        global scheduled_message
        scheduled_message["user"] = user
        scheduled_message["message"] = message
        scheduled_message["time"] = time
        await interaction.response.send_message(
            f"Message to {user.name} scheduled for {time}.", ephemeral=True
        )
    else:
        await interaction.response.defer()
        for _ in range(times):
            try:
                await user.send(message)
                await asyncio.sleep(0.5)
            except discord.Forbidden:
                await interaction.edit_original_response(
                    content=f"Failed to send a DM to {user.name}. They might have DMs disabled or the bot doesn't share a server with them.",
                )
                return
            except discord.HTTPException:
                await interaction.edit_original_response(
                    content=f"Failed to send a DM to {user.name} due to an HTTP exception.",
                )
                return
        await interaction.edit_original_response(
            content=f"Successfully sent {times} message(s) to {user.name}.",
        )


@bot.tree.command(
    name="cancel_dm",
    description="Cancel a scheduled DM",
)
async def cancel_dm_slash(interaction: discord.Interaction):
    global scheduled_message
    if scheduled_message["user"] is not None:
        scheduled_message = {"user": None, "message": "", "time": ""}
        await interaction.response.send_message(
            "Scheduled message cancelled.", ephemeral=True
        )
    else:
        await interaction.response.send_message(
            "No message is currently scheduled.", ephemeral=True
        )


@bot.tree.command(
    name="server_stats",
    description="Display server statistics",
)
async def server_stats_slash(
    interaction: discord.Interaction, hide_message: bool = True
):
    guild = interaction.guild
    member_count = guild.member_count
    text_channels = len(guild.text_channels)
    voice_channels = len(guild.voice_channels)
    role_count = len(guild.roles)

    embed = discord.Embed(title="Server Statistics", color=discord.Color.dark_purple())
    embed.add_field(name="Members:", value=str(member_count), inline=False)
    embed.add_field(name="Text Channels:", value=str(text_channels), inline=False)
    embed.add_field(name="Voice Channels:", value=str(voice_channels), inline=False)
    embed.add_field(name="Roles:", value=str(role_count), inline=False)

    await interaction.response.send_message(embed=embed, ephemeral=hide_message)


@bot.tree.command(
    name="avatar",
    description="Display the avatar of a user",
)
async def avatar_slash(
    interaction: discord.Interaction,
    user: discord.User = None,
    hide_message: bool = True,
):
    user = user or interaction.user
    avatar_url = user.avatar.url

    embed = discord.Embed(
        title=f"{user.name}'s avatar", color=discord.Color.dark_purple()
    )
    embed.set_image(url=avatar_url)

    await interaction.response.send_message(embed=embed, ephemeral=hide_message)


@bot.tree.command(
    name="user_info",
    description="Display information about a user",
)
async def user_info_slash(
    interaction: discord.Interaction,
    user: discord.Member = None,
    hide_message: bool = True,
):
    user = user or interaction.user
    guild = interaction.guild

    embed = discord.Embed(title="User Info", color=discord.Color.dark_purple())
    embed.set_thumbnail(url=user.avatar.url)
    embed.add_field(name="Name:", value=user.name, inline=False)
    embed.add_field(name="ID:", value=user.id, inline=False)
    embed.add_field(name="Discriminator:", value=user.discriminator, inline=False)
    embed.add_field(name="Bot Account:", value=user.bot, inline=False)
    embed.add_field(name="Status:", value=str(user.status), inline=False)
    embed.add_field(name="Number of Roles:", value=len(user.roles), inline=False)
    embed.add_field(
        name="Boosting:", value="Yes" if user.premium_since else "No", inline=False
    )
    embed.add_field(
        name="Created at:",
        value=user.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        inline=False,
    )
    embed.add_field(
        name="Joined at:",
        value=user.joined_at.strftime("%Y-%m-%d %H:%M:%S") if user.joined_at else "N/A",
        inline=False,
    )
    embed.add_field(name="Highest Role:", value=user.top_role.name, inline=False)

    await interaction.response.send_message(embed=embed, ephemeral=hide_message)


@bot.tree.command(
    name="uptime",
    description="Display the bot's uptime",
)
async def uptime_slash(interaction: discord.Interaction, hide_message: bool = True):
    global start_time
    uptime = datetime.utcnow() - start_time
    hours, remainder = divmod(int(uptime.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)
    days, hours = divmod(hours, 24)

    embed = discord.Embed(title="Uptime", color=discord.Color.dark_purple())
    embed.add_field(
        name="Uptime:", value=f"{days}d: {hours}h: {minutes}m: {seconds}s", inline=False
    )

    await interaction.response.send_message(embed=embed, ephemeral=hide_message)


@bot.tree.command(
    name="joke",
    description="Get a random joke",
)
async def joke_slash(interaction: discord.Interaction, hide_message: bool = True):
    response = requests.get("https://official-joke-api.appspot.com/random_joke")
    data = response.json()

    joke = f"{data['setup']}\n{data['punchline']}"

    await interaction.response.send_message(joke, ephemeral=hide_message)


@bot.tree.command(
    name="cat",
    description="Get cute cat images",
)
async def cat_slash(
    interaction: discord.Interaction,
    number_of_images: int = 1,
    hide_message: bool = True,
):
    number_of_images = max(min(number_of_images, 5), 1)

    for i in range(number_of_images):
        response = requests.get(
            "https://api.thecatapi.com/v1/images/search?category_ids=1"
        )
        data = response.json()

        cat_image_url = data[0]["url"]

        embed = discord.Embed(title="Cute Cat")
        embed.set_image(url=cat_image_url)

        if i == 0:
            await interaction.response.send_message(embed=embed, ephemeral=hide_message)
        else:
            await interaction.followup.send(embed=embed, ephemeral=hide_message)


async def city_autocompletion(
    interaction: discord.Interaction, current: str
) -> typing.List[app_commands.Choice[str]]:
    data = []

    for city in CITY:
        if current.lower() in city.lower():
            data.append(app_commands.Choice(name=city, value=city))

    return data


@bot.tree.command(name="weather", description="Get the current weather in a city")
@app_commands.autocomplete(city=city_autocompletion)
async def weather_slash(
    interaction: discord.Interaction, city: str, forecast: bool = False
):
    if forecast:
        base_url = "http://api.openweathermap.org/data/2.5/forecast"
    else:
        base_url = "http://api.openweathermap.org/data/2.5/weather"

    response = requests.get(
        base_url,
        params={
            "q": city,
            "appid": api_weather,
            "units": "metric",
        },
    )

    data = response.json()

    if int(data["cod"]) != 200:
        await interaction.response.send_message(
            f"Error: {data.get('message', 'Unknown error')}", ephemeral=True
        )
        return

    if forecast:
        tomorrow = datetime.now() + timedelta(days=1)
        tomorrow_forecast = next(
            (
                item
                for item in data["list"]
                if datetime.fromtimestamp(item["dt"]).date() == tomorrow.date()
            ),
            None,
        )

        if tomorrow_forecast is None:
            await interaction.response.send_message(
                f"No forecast data available for tomorrow in {city.title()}",
                ephemeral=True,
            )
            return

        weather_description = tomorrow_forecast["weather"][0]["description"]
        temperature = tomorrow_forecast["main"]["temp"]
        weather_icon = tomorrow_forecast["weather"][0]["icon"]
        will_rain = any(
            weather["main"] == "Rain" for weather in tomorrow_forecast["weather"]
        )
    else:
        weather_description = data["weather"][0]["description"]
        temperature = data["main"]["temp"]
        weather_icon = data["weather"][0]["icon"]
        will_rain = any(weather["main"] == "Rain" for weather in data["weather"])

    embed = discord.Embed(title=f"Weather in {city.title()}")
    embed.add_field(name="Description", value=weather_description, inline=False)
    embed.add_field(name="Temperature", value=f"{temperature}°C", inline=False)
    embed.add_field(
        name="Will it rain?", value="Yes" if will_rain else "No", inline=False
    )
    embed.set_thumbnail(url=f"http://openweathermap.org/img/w/{weather_icon}.png")

    await interaction.response.send_message(embed=embed)


async def name_autocompletion(
    interaction: discord.Interaction, current: str
) -> typing.List[app_commands.Choice[str]]:
    action = interaction.namespace.action
    data = []
    birthdays = load_birthdays_from_db()

    if action == "add":
        for member in interaction.guild.members:
            if current.lower() in member.name.lower() and member.name not in birthdays:
                data.append(app_commands.Choice(name=member.name, value=member.name))
    elif action == "delete":
        for name in birthdays.keys():
            if current.lower() in name.lower():
                data.append(app_commands.Choice(name=name, value=name))

    # Limit the list to 25 items
    limited_data = data[:25]

    return limited_data


async def action_autocompletion(
    interaction: discord.Interaction, current: str
) -> typing.List[app_commands.Choice[str]]:
    actions = ["add", "delete", "display", "next"]
    data = []

    for action in actions:
        if current.lower() in action.lower():
            data.append(app_commands.Choice(name=action, value=action))

    return data


def load_birthdays_from_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT username, birthdate FROM birthdays")
    rows = cur.fetchall()
    birthdays = {row[0]: row[1].strftime("%d-%m-%Y") for row in rows}
    cur.close()
    conn.close()
    return birthdays


def save_birthday_to_db(username, birthdate):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # Parse the input date and convert it to YYYY-MM-DD format
        parsed_date = datetime.strptime(birthdate, "%d-%m-%Y").strftime("%Y-%m-%d")

        cur.execute(
            """
            INSERT INTO birthdays (username, birthdate)
            VALUES (%s, %s)
            ON CONFLICT (username) DO UPDATE SET birthdate = EXCLUDED.birthdate
            """,
            (username, parsed_date),
        )
        conn.commit()
    except Exception as e:
        logging.error(f"Error saving birthday to DB: {e}")
    finally:
        cur.close()
        conn.close()


def delete_birthday_from_db(name):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM birthdays WHERE username = %s", (name,))
    conn.commit()
    cur.close()
    conn.close()


@bot.tree.command(name="birthday", description="Set your birthday")
@app_commands.describe(
    action="Add, delete, display, or get the number of days before the next birthday"
)
@app_commands.autocomplete(name=name_autocompletion)
@app_commands.autocomplete(action=action_autocompletion)
async def birthday_slash(
    interaction: discord.Interaction,
    action: str,
    name: str = None,
    birthdate: str = None,
    hide_message: bool = True,
):
    try:
        if action == "add":
            if name and birthdate:
                birthdate = parse(birthdate).strftime("%d-%m-%Y")
                save_birthday_to_db(name, birthdate)
                embed = Embed(
                    title="🎉 Birthday Added",
                    description=f"Added birthday for **{name}** on {birthdate}",
                    color=Colour.green(),
                )
            else:
                embed = Embed(
                    title="❌ Error",
                    description="You must provide a name and birthdate to add a birthday.",
                    color=Colour.red(),
                )
            await interaction.response.send_message(
                embeds=[embed], ephemeral=hide_message
            )

        elif action == "delete":
            if name:
                delete_birthday_from_db(name)
                embed = Embed(
                    title="🗑️ Birthday Deleted",
                    description=f"Deleted birthday for **{name}**",
                    color=Colour.green(),
                )
            else:
                embed = Embed(
                    title="❌ Error",
                    description="You must provide a valid name to delete a birthday.",
                    color=Colour.red(),
                )
            await interaction.response.send_message(
                embeds=[embed], ephemeral=hide_message
            )

        elif action == "display":
            birthdays = load_birthdays_from_db()
            if name:
                if name in birthdays:
                    embed = Embed(
                        title=f"🎂 Birthday for {name}",
                        description=f"**{name}**: {birthdays[name]}",
                        color=Colour.blue(),
                    )
                else:
                    embed = Embed(
                        title="❌ No Birthday Found",
                        description=f"No birthday found for **{name}**.",
                        color=Colour.red(),
                    )
            else:
                if birthdays:
                    embed = Embed(
                        title="📅 Birthdays",
                        color=Colour.blue(),
                    )
                    for name, birthdate in birthdays.items():
                        embed.add_field(name=name, value=birthdate, inline=False)
                else:
                    embed = Embed(
                        title="❌ No Birthdays",
                        description="No birthdays to display.",
                        color=Colour.red(),
                    )
            await interaction.response.send_message(
                embeds=[embed], ephemeral=hide_message
            )

        elif action == "next":
            if name:
                birthdays = load_birthdays_from_db()
                if name in birthdays:
                    birthdate = datetime.strptime(birthdays[name], "%Y-%m-%d")
                    now = datetime.now()
                    next_birthday = birthdate.replace(year=now.year)
                    if now > next_birthday:
                        next_birthday = next_birthday.replace(year=now.year + 1)
                    days_left = (next_birthday - now).days
                    embed = Embed(
                        title=f"🎉 Next Birthday for {name}",
                        description=f"{days_left} days until **{name}'s** next birthday.",
                        color=Colour.blue(),
                    )
                else:
                    embed = Embed(
                        title="❌ No Birthday Found",
                        description=f"No birthday found for **{name}**.",
                        color=Colour.red(),
                    )
            else:
                embed = Embed(
                    title="❌ No Birthdays",
                    description="No birthdays to display.",
                    color=Colour.red(),
                )
            await interaction.response.send_message(
                embeds=[embed], ephemeral=hide_message
            )

    except Exception as e:
        logging.error(f"Error in birthday command: {e}")
        await interaction.response.send_message(
            "An error occurred while processing your request.",
            ephemeral=True,
        )


def log_message_to_db(message_data):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO message_logs (encoded_message) VALUES (%s)",
        (json.dumps(message_data),),
    )
    conn.commit()
    cur.close()
    conn.close()


def log_message_to_db(message_data):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO message_logs (encoded_message) VALUES (%s)",
        (json.dumps(message_data),),
    )
    conn.commit()
    cur.close()
    conn.close()


# Define the list of banned words and the ban duration
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
    # Add more words or phrases to this list as needed
]

@bot.event
async def on_message(message: discord.Message):
    # Ignore messages from bots
    if message.author.bot:
        return

    # Convert message to lowercase and check each word
    message_words = message.content.lower().split()
    # Check if any banned word appears as a full word match
    for word in message_words:
        if word in [banned.lower() for banned in BANNED_WORDS]:
            try:
                # Store user roles before ban
                member = message.author
                user_roles = [role for role in member.roles if role.name != "@everyone"]
                
                # Ban the user
                await message.guild.ban(
                    message.author,
                    reason=f"Used banned word: {word}",
                    delete_message_seconds=0
                )
                print(f"Ban applied to {message.author.name} for using banned word: {word}")
                
                # Delete the message
                await message.delete()
                print(f"Message deleted: {message.content}")

                # Send a more detailed notification message
                ban_notification = (
                    f"🚫 {message.author.mention} has been temporarily banned for using the banned word: **{word}**\n\n"
                    f"⚠️ Reminder: The following words are banned:\n"
                    f"```\n{', '.join(BANNED_WORDS)}\n```\n"
                    "The ban will last for 1 minute."
                )

                await message.channel.send(
                    ban_notification,
                    delete_after=10
                )

                try:
                    # Send DM to banned user with more details
                    await message.author.send(
                        f"You have been temporarily banned from {message.guild.name} for using the banned word: **{word}**\n"
                        f"The ban will last for 1 minute.\n\n"
                        f"⚠️ Please note that the following words are banned:\n"
                        f"```\n{', '.join(BANNED_WORDS)}```"
                    )
                    print(f"Ban notification sent to {message.author.name}")
                except discord.Forbidden:
                    pass  # Can't DM user
                return

            except discord.Forbidden:
                await message.channel.send(
                    "I don't have permission to ban this user.",
                    delete_after=10
                )
            except discord.HTTPException as e:
                await message.channel.send(
                    f"Failed to ban user: {str(e)}",
                    delete_after=10
                )
                print(f"Failed to ban user: {str(e)}")
            return

    # Process other commands
    await bot.process_commands(message)

    excluded_channels = load_excluded_channels()
    if message.author == bot.user or message.channel.id in excluded_channels:
        return

    message_data = {
        "user": message.author.name,
        "message": message.content,
        "time": message.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        "attachments": (
            [attachment.url for attachment in message.attachments]
            if message.attachments
            else "No attachments"
        ),
        "guild": message.guild.name if message.guild else "Direct Message",
        "channel": message.channel.name if message.guild else "Direct Message",
    }

    log_message_to_db(message_data)
    await bot.process_commands(message)


@bot.event
async def on_message_edit(before, after):
    excluded_channels = load_excluded_channels()
    if before.author == bot.user or before.channel.id in excluded_channels:
        return

    edit_data = {
        "user": before.author.name,
        "old_message": before.content,
        "new_message": after.content,
        "time": (
            after.edited_at.strftime("%Y-%m-%d %H:%M:%S")
            if after.edited_at
            else before.created_at.strftime("%Y-%m-%d %H:%M:%S")
        ),
        "guild": before.guild.name if before.guild else "Direct Message",
        "channel": before.channel.name if before.guild else "Direct Message",
    }

    log_message_to_db(edit_data)
    await bot.process_commands(after)


async def action_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> typing.List[app_commands.Choice[str]]:
    choices = ["add", "remove", "list"]
    return [
        app_commands.Choice(name=choice, value=choice)
        for choice in choices
        if current.lower() in choice.lower()
    ]


async def channel_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> typing.List[app_commands.Choice[str]]:
    action = interaction.namespace.action
    excluded_channels = load_excluded_channels()
    if action == "remove":
        return [
            app_commands.Choice(
                name=interaction.guild.get_channel(c).name, value=str(c)
            )
            for c in excluded_channels
            if interaction.guild.get_channel(c)
            and current.lower() in interaction.guild.get_channel(c).name.lower()
        ]
    else:  # Show all channels for the "add" action, excluding already excluded channels
        return [
            app_commands.Choice(name=channel.name, value=str(channel.id))
            for channel in interaction.guild.text_channels
            if channel.id not in excluded_channels
            and current.lower() in channel.name.lower()
        ]


@bot.tree.command(
    name="manage_logging_channels",
    description="Manage the logging channels to not log messages from",
)
@app_commands.describe(
    action="Add, remove or list the channels to exclude from logging messages",
    channel="Specify the channel to add or remove",
)
@app_commands.autocomplete(action=action_autocomplete)
@app_commands.autocomplete(channel=channel_autocomplete)
async def manage_logging_channels_slash(
    interaction: discord.Interaction,
    action: str,
    channel: str = None,
    hide_message: bool = True,
):
    channels = load_excluded_channels()

    if action == "add":
        if channel is None:
            await interaction.response.send_message(
                "Please specify a channel to add.", ephemeral=True
            )
            return

        channel = interaction.guild.get_channel(int(channel))
        if channel.id not in channels:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO logging_channels (channel_id) VALUES (%s) ON CONFLICT DO NOTHING",
                (channel.id,),
            )
            conn.commit()
            cur.close()
            conn.close()

            await interaction.response.send_message(
                f"Added channel {channel.mention} to the list of channels to exclude from logging.",
                ephemeral=hide_message,
            )
        else:
            await interaction.response.send_message(
                f"Channel {channel.mention} is already in the list of channels to exclude from logging.",
                ephemeral=hide_message,
            )

    elif action == "remove":
        if channel is None:
            await interaction.response.send_message(
                "Please specify a channel to remove.", ephemeral=True
            )
            return

        channel = interaction.guild.get_channel(int(channel))
        if channel.id in channels:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute(
                "DELETE FROM logging_channels WHERE channel_id = %s", (channel.id,)
            )
            conn.commit()
            cur.close()
            conn.close()

            await interaction.response.send_message(
                f"Removed channel {channel.mention} from the list of channels to exclude from logging.",
                ephemeral=hide_message,
            )
        else:
            await interaction.response.send_message(
                f"Channel {channel.mention} is not in the list of channels to exclude from logging.",
                ephemeral=hide_message,
            )

    elif action == "list":
        if channels:
            channel_mentions = [
                interaction.guild.get_channel(c).mention
                for c in channels
                if interaction.guild.get_channel(c)
            ]
            channels_list = "\n".join(channel_mentions)
            await interaction.response.send_message(
                f"Channels to exclude from logging:\n{channels_list}",
                ephemeral=hide_message,
            )
        else:
            await interaction.response.send_message(
                "No channels are excluded from logging.", ephemeral=hide_message
            )


def load_excluded_channels():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT channel_id FROM logging_channels")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [row[0] for row in rows]


class LogEmbed(ui.View):
    def __init__(self, logs):
        super().__init__()
        self.logs = logs
        self.current_page = 0
        self.total_pages = (len(logs) + 24) // 25  # Calculate total pages
        self.add_page_selector()

    @ui.button(label="Previous", style=ButtonStyle.primary)
    async def previous_button(self, interaction: Interaction, button: ui.Button):
        if self.current_page > 0:
            self.current_page -= 1
            await interaction.response.edit_message(embed=self.get_embed(), view=self)
        else:
            await interaction.response.send_message(
                "You are already on the first page.", ephemeral=True
            )

    @ui.button(label="Next", style=ButtonStyle.primary)
    async def next_button(self, interaction: Interaction, button: ui.Button):
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            await interaction.response.edit_message(embed=self.get_embed(), view=self)
        else:
            await interaction.response.send_message(
                "You are already on the last page.", ephemeral=True
            )

    @ui.select(placeholder="Select a page...", options=[])
    async def select_page(self, interaction: Interaction, select: ui.Select):
        self.current_page = int(select.values[0])
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    def add_page_selector(self):
        options = [
            SelectOption(label=str(i + 1), value=str(i))
            for i in range(self.total_pages)
        ]
        self.select_page.options = options

    def get_embed(self):
        start = self.current_page * 25
        end = start + 25
        embed = Embed(
            title=f"📝 Logs Page {self.current_page + 1}/{self.total_pages} 📝",
            color=0x4B0082,
        )
        embed.timestamp = datetime.now()
        total_characters = 0
        embed.set_footer(text="Tess Spy Agency")
        # Add a field with a clickable link
        embed.add_field(
            name="Visit Our Website",
            value="Click [here](https://spy.tessdev.fr) to visit the website.",
            inline=False,
        )

        for i, log in enumerate(self.logs[start:end], start=start + 1):
            formatted_log = self.format_log(log)
            total_characters += len(formatted_log)
            if total_characters > 6000:
                embed.add_field(
                    name="Warning",
                    value="Log content truncated due to Discord embed limits.",
                    inline=False,
                )
                break
            if len(embed.fields) >= 25:
                break
            embed.add_field(name=f"Log {i}", value=formatted_log, inline=False)

        return embed

    def format_log(self, log):
        user = log.get("user", "Unknown User")
        message = log.get("message", "No message").strip()
        time = log.get("time", "Unknown time")
        attachments = log.get("attachments", "No attachments")
        guild = log.get("guild", "Unknown guild")
        channel = log.get("channel", "Unknown channel")

        if len(message) > 100:
            message = message[:100] + "..."

        formatted_log = (
            f"**User**: {user}\n"
            f"**Message**: {message}\n"
            f"**Time**: {time}\n"
            f"**Attachments**: {attachments}\n"
            f"**Guild**: {guild}\n"
            f"**Channel**: {channel}\n"
        )

        # Ensure no field exceeds 1024 characters
        if len(formatted_log) > 1024:
            formatted_log = formatted_log[:1021] + "..."

        return formatted_log


@bot.tree.command(
    name="read_logs",
    description="Read the content of the message logs",
)
@is_owner()
async def read_logs_slash(interaction: discord.Interaction, hide_message: bool = True):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT encoded_message FROM message_logs")
    rows = cur.fetchall()
    logs = [json.loads(row[0]) for row in rows]
    cur.close()
    conn.close()

    if logs:
        view = LogEmbed(logs)
        await interaction.response.send_message(
            embed=view.get_embed(), view=view, ephemeral=hide_message
        )
    else:
        await interaction.response.send_message(
            "No valid logs found.", ephemeral=hide_message
        )


@bot.tree.command(
    name="delete_all_logs",
    description="Delete the content of all the message logs",
)
@is_owner()
async def delete_all_logs_slash(
    interaction: discord.Interaction, hide_message: bool = True
):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM message_logs")
    conn.commit()
    cur.close()
    conn.close()

    await interaction.response.send_message(
        "All logs have been deleted.", ephemeral=hide_message
    )


async def crafty_action_autocompletion(
    interaction: discord.Interaction, current: str
) -> typing.List[app_commands.Choice[str]]:
    valid_actions = [
        "start_server",
        "stop_server",
        "restart_server",
        "backup_server",
    ]
    data = []

    for action in valid_actions:
        if current.lower() in action.lower():
            data.append(app_commands.Choice(name=action, value=action))

    return data


# Global variables
servers = []


@tasks.loop(seconds=10)  # Adjust the interval as needed
async def update_servers():
    global servers
    url = "https://crafty.tessdev.fr/api/v2/servers"
    headers = {"Authorization": f"Bearer {crafty_api_token}"}

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            data = await response.json()
            if response.status == 200:
                servers = [
                    {"uuid": server["server_id"], "name": server["server_name"]}
                    for server in data.get("data", [])
                ]
                # Check if the log file exists
                if not os.path.exists("log_once_per_session.txt"):
                    logging.info("Successfully fetched server data.")
                    # Create the file to mark the message as logged
                    with open("log_once_per_session.txt", "w") as f:
                        f.write("Logged")
            else:
                logging.error("Failed to fetch server data.")
                logging.error("Attempting to re-authenticate...")
                await authenticate()


@update_servers.before_loop
async def before_update_servers():
    await bot.wait_until_ready()


async def server_uuid_autocompletion(
    interaction: discord.Interaction, current: str
) -> typing.List[app_commands.Choice[str]]:
    # Filter server UUIDs and names based on the current input
    filtered_servers = [
        server
        for server in servers
        if current.lower() in server["uuid"].lower()
        or current.lower() in server["name"].lower()
    ]
    return [
        app_commands.Choice(
            name=f"{server['name']} ({server['uuid']})", value=server["uuid"]
        )
        for server in filtered_servers[:25]
    ]  # Limit to 25 choices


@bot.tree.command(
    name="crafty_control",
    description="Perform an action on a server",
)
@app_commands.autocomplete(action=crafty_action_autocompletion)
@app_commands.autocomplete(server_uuid=server_uuid_autocompletion)
async def server_action_slash(
    interaction: discord.Interaction,
    server_uuid: str,
    action: str,
    hide_message: bool = True,
):
    # Validate the action
    valid_actions = [
        "start_server",
        "stop_server",
        "restart_server",
        "backup_server",
    ]
    if action not in valid_actions:
        await interaction.response.send_message(
            f"Invalid action. Please choose from {', '.join(valid_actions)}.",
            ephemeral=True,
        )
        return

    # Construct the API request
    url = f"https://crafty.tessdev.fr/api/v2/servers/{server_uuid}/action/{action}"
    headers = {
        "Authorization": f"Bearer {crafty_api_token}",
        "Accept": "application/json",
    }

    # Send the request
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers) as response:
            data = await response.json()
            if response.status == 200 and data.get("status") == "ok":
                message = "Action performed successfully."
                if "new_server_id" in data.get("data", {}):
                    message += f" New server ID: {data['data']['new_server_id']}"
                await interaction.response.send_message(message, ephemeral=hide_message)
            else:
                await interaction.response.send_message(
                    "Failed to perform the action on the server.",
                    ephemeral=hide_message,
                )


@bot.tree.context_menu(name="Gay to Gay")
async def add_text_to_image_gay(
    interaction: discord.Interaction, message: discord.Message
):
    await add_text_to_image(interaction, message, "Gay")


@bot.tree.context_menu(name="Ratio to Ratio")
async def add_text_to_image_ratio(
    interaction: discord.Interaction, message: discord.Message
):
    await add_text_to_image(interaction, message, "Ratio + don't care + didn't ask")


@bot.tree.context_menu(name="Féminisme to Féminisme")
async def add_text_to_image_feminism(
    interaction: discord.Interaction, message: discord.Message
):
    await add_text_to_image(interaction, message, "Femme + Féministe + Féminisme")


async def add_text_to_image(
    interaction: discord.Interaction, message: discord.Message, text: str
):
    await interaction.response.defer()  # Acknowledge the interaction to avoid timeout

    # Check for attachments first (like an image or GIF)
    if message.attachments:
        attachment = message.attachments[0]
        # Check if it's a GIF or image
        if (
            attachment.content_type.startswith("image/")
            or attachment.content_type == "image/gif"
        ):
            await process_attachment(interaction, attachment, text)
        else:
            await interaction.followup.send(
                "Unsupported file type. Please upload an image or GIF.", ephemeral=True
            )

    # If no attachments, look for URLs in the message
    elif message.content:
        # Extract URLs from the message
        urls = find_urls_in_string(message.content)
        if urls:
            for url in urls:
                # Check if the URL is a Tenor GIF
                if "tenor.com" in url:
                    tenor_id = extract_tenor_id(url)
                    if tenor_id:
                        gif_url = get_tenor_gif_direct_url(tenor_id)
                        if gif_url:
                            await process_image_url(
                                interaction, gif_url, text, is_gif=True
                            )
                        else:
                            await interaction.followup.send(
                                "Failed to retrieve Tenor GIF.", ephemeral=True
                            )
                    else:
                        await interaction.followup.send(
                            "Failed to extract Tenor GIF ID.", ephemeral=True
                        )

                # Check if it's a regular GIF URL
                elif url.lower().endswith(".gif"):
                    await process_image_url(interaction, url, text, is_gif=True)

                # Handle other image URLs
                else:
                    await process_image_url(interaction, url, text)
        else:
            await interaction.followup.send(
                "No valid content found (image, GIF, or URL).", ephemeral=True
            )

    # Handle stickers (if applicable)
    elif message.stickers:
        await process_sticker(interaction, message.stickers[0], text)

    else:
        await interaction.followup.send(
            "No valid content found (image, GIF, Tenor GIF, sticker, or text).",
            ephemeral=True,
        )


# Your find_urls_in_string function
def find_urls_in_string(string):
    regex = r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))"
    urls = re.findall(regex, string)
    return [x[0] for x in urls]


# Extract Tenor ID from Tenor URL
def extract_tenor_id(tenor_url):
    match = re.search(r"-(\d+)$", tenor_url)
    if match:
        return match.group(1)
    return None


# Fetch the direct GIF URL from Tenor using the Google API
def get_tenor_gif_direct_url(tenor_id):
    try:
        url = f"https://tenor.googleapis.com/v2/posts?ids={tenor_id}&key={tenor_api_key}&client_key={tess_bot_id}"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            # Fetch the first result and extract the GIF URL
            return data["results"][0]["media_formats"]["gif"]["url"]
        else:
            print(f"Failed to fetch GIF, status code: {response.status_code}")
            return None
    except Exception as e:
        print(f"Error fetching Tenor GIF: {e}")
        return None


async def process_attachment(interaction, attachment, text):
    try:
        response = requests.get(attachment.url)
        if response.status_code != 200:
            await interaction.followup.send(
                f"Failed to download content, status code: {response.status_code}",
                ephemeral=True,
            )
            return

        if attachment.content_type == "image/gif":
            gif_bytes = io.BytesIO(response.content)
            await process_gif(interaction, gif_bytes, text)
        else:
            image_bytes = io.BytesIO(response.content)
            await process_image(interaction, image_bytes, text)
    except Exception as e:
        await interaction.followup.send(
            f"An error occurred while processing the attachment: {e}", ephemeral=True
        )


async def process_image_url(interaction, url, text, is_gif=False):
    try:
        response = requests.get(url)
        if response.status_code == 200:
            image_bytes = io.BytesIO(response.content)
            if is_gif:
                await process_gif(interaction, image_bytes, text)
            else:
                await process_image(interaction, image_bytes, text)
        else:
            await interaction.followup.send(
                f"Failed to download content, status code: {response.status_code}",
                ephemeral=True,
            )
    except Exception as e:
        await interaction.followup.send(
            f"An error occurred while processing the URL: {e}", ephemeral=True
        )


async def process_image(interaction, image_bytes, text):
    with Image.open(image_bytes) as img:
        draw = ImageDraw.Draw(img)
        font_path = os.path.join(os.getcwd(), "data", "Roboto-Bold.ttf")
        font, text_width, text_height = get_fitting_font(
            text, img, draw, font_path, 40, 15
        )
        x = (img.width - text_width) / 2
        y = (img.height - text_height) / 2
        draw.text((x, y), text, fill="white", font=font)

        output_buffer = io.BytesIO()
        img.save(output_buffer, format="PNG")
        output_buffer.seek(0)
        await interaction.followup.send(
            file=discord.File(fp=output_buffer, filename="edited_image.png")
        )


async def process_gif(interaction, gif_bytes, text):
    try:
        with Image.open(gif_bytes) as img:
            if img.format != "GIF":
                raise ValueError("Not a valid GIF format")

            frames = []
            durations = []
            for frame in ImageSequence.Iterator(img):
                frame = frame.convert("RGBA")  # Convert to RGBA to handle transparency
                draw = ImageDraw.Draw(frame)
                font_path = os.path.join(os.getcwd(), "data", "Roboto-Bold.ttf")
                font, text_width, text_height = get_fitting_font(
                    text, frame, draw, font_path, 40, 15
                )
                x = (frame.width - text_width) / 2
                y = (frame.height - text_height) / 2
                draw.text((x, y), text, fill="white", font=font)
                frames.append(frame.copy())  # Add the modified frame
                durations.append(img.info["duration"])  # Preserve the frame duration

            # Save the frames into a GIF without compression
            output_buffer = io.BytesIO()
            frames[0].save(
                output_buffer,
                format="GIF",
                save_all=True,
                append_images=frames[1:],  # Add all frames
                duration=durations,  # Set frame durations
                loop=0,  # Keep the loop count
                optimize=False,  # Do not optimize (better quality)
                transparency=0,  # Preserve transparency
                disposal=2,  # Keep the disposal method for each frame
            )
            output_buffer.seek(0)

            # Send the edited GIF
            await interaction.followup.send(
                file=discord.File(fp=output_buffer, filename="edited_image.gif")
            )
    except Exception as e:
        await interaction.followup.send(
            f"An error occurred while processing the GIF: {e}", ephemeral=True
        )


async def process_sticker(interaction, sticker, text):
    try:
        sticker_url = sticker.url if hasattr(sticker, "url") else sticker.image_url
        response = requests.get(sticker_url)
        sticker_bytes = io.BytesIO(response.content)
        await process_image(interaction, sticker_bytes, text)
    except Exception as e:
        await interaction.followup.send(
            f"An error occurred while processing the sticker: {e}", ephemeral=True
        )


def get_fitting_font(text, image, draw, font_path, base_font_size, min_font_size):
    font_size = base_font_size
    font = ImageFont.truetype(font_path, font_size)
    text_bbox = draw.textbbox((0, 0), text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]

    while (
        text_width > image.size[0] * 0.8 or text_height > image.size[1] * 0.2
    ) and font_size > min_font_size:
        font_size -= 1
        font = ImageFont.truetype(font_path, font_size)
        text_bbox = draw.textbbox((0, 0), text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]

    return font, text_width, text_height


# Define a context menu command to resize an image
@bot.tree.context_menu(name="Image to emoji")
async def resize_and_upload_as_emoji(
    interaction: discord.Interaction, message: discord.Message
):
    if message.attachments:
        # Get the first attachment
        attachment = message.attachments[0]
        if attachment.content_type.startswith("image/"):
            # Download the image
            response = requests.get(attachment.url)
            image_bytes = io.BytesIO(response.content)

            # Open the image using Pillow
            with Image.open(image_bytes) as img:
                # Resize the image to fit within a 128x128 pixel boundary using LANCZOS filter
                img.thumbnail((128, 128), Image.LANCZOS)

                # Save the resized image to a BytesIO object
                output_buffer = io.BytesIO()
                img.save(output_buffer, format="PNG", optimize=True)
                output_buffer.seek(0)

                # Check if the file size is greater than 256 KB
                if output_buffer.getbuffer().nbytes > 256 * 1024:
                    await interaction.response.send_message(
                        "Image is too large to be uploaded as an emoji (must be under 256 KB).",
                        ephemeral=True,
                    )
                    return

                # Upload the image as an emoji to the server
                emoji_name = "".join(
                    random.choices(string.ascii_letters + string.digits, k=5)
                )
                guild = interaction.guild
                try:
                    emoji = await guild.create_custom_emoji(
                        name=emoji_name, image=output_buffer.read()
                    )
                    await interaction.response.send_message(
                        f"Emoji created successfully: <:{emoji.name}:{emoji.id}>",
                        ephemeral=True,
                    )
                except discord.HTTPException as e:
                    await interaction.response.send_message(
                        f"Failed to create emoji: {e}", ephemeral=True
                    )
        else:
            await interaction.response.send_message(
                "The attachment is not an image.", ephemeral=True
            )
    else:
        await interaction.response.send_message(
            "No attachment found in the message.", ephemeral=True
        )


# Define a context menu command to resize an image
@bot.tree.context_menu(name="Image to Sticker")
async def resize_image(interaction: discord.Interaction, message: discord.Message):
    if message.attachments:
        # Get the first attachment
        attachment = message.attachments[0]
        if attachment.content_type.startswith("image/"):
            # Download the image
            response = requests.get(attachment.url)
            image_bytes = io.BytesIO(response.content)

            # Open the image using Pillow
            with Image.open(image_bytes) as img:
                # Save the resized image to a BytesIO object with maximum size constraint
                output_buffer = io.BytesIO()
                img.save(output_buffer, format="PNG", optimize=True)
                output_buffer.seek(0)

                # Check if the file size is greater than 512 KB
                if output_buffer.getbuffer().nbytes > 512 * 1024:
                    # If it is, reduce the quality and retry
                    quality = 85
                    while (
                        output_buffer.getbuffer().nbytes > 512 * 1024 and quality > 10
                    ):
                        output_buffer = io.BytesIO()  # Reset buffer
                        # Convert image to RGB mode before saving as JPEG
                        img.convert("RGB").save(
                            output_buffer, format="JPEG", quality=quality, optimize=True
                        )
                        output_buffer.seek(0)
                        quality -= 5

                # Send the resized image back
                await interaction.response.send_message(
                    file=discord.File(fp=output_buffer, filename="resized_image.png")
                )
        else:
            await interaction.response.send_message(
                "The attachment is not an image.", ephemeral=True
            )
    else:
        await interaction.response.send_message(
            "No attachment found in the message.", ephemeral=True
        )

@bot.tree.command(name="clear")
@app_commands.describe(amount="The number of messages to delete")
async def clear(interaction: discord.Interaction, amount: int, ephemeral: bool = True):
    if amount < 1:
        await interaction.response.send_message("Please specify a positive number of messages to delete.", ephemeral=True)
        return

    await interaction.channel.purge(limit=amount)
    await interaction.response.send_message(
        f"Cleared {amount} messages.", ephemeral=ephemeral
    )


@bot.event
async def on_ready():
    await bot.change_presence(
        activity=discord.Activity(
            # type=discord.ActivityType.watching,
            name="Watching you in the shower",
            assets={
                "large_image": "aide",  # Name of the large image you uploaded
                "large_text": "Watching something",  # Tooltip when hovering over the large image
                "small_image": "aide",  # Name of the small image you uploaded
                "small_text": "Watching something",  # Tooltip when hovering over the small image
            },
        ),
        status=discord.Status.dnd,
    )

    logging.info(f"Logged in as {bot.user.name} - {bot.user.id}")
    logging.info(f"{bot.user.name}_BOT is ready to go !")
    check_time.start()
    update_servers.start()
    global start_time
    start_time = datetime.now()
    logging.info(f"Bot started at {start_time}")

    try:
        synced = await bot.tree.sync()
        logging.info(f"Synced {len(synced)} commands")
    except Exception as e:
        logging.error(f"Failed to sync commands: {e}")
    print("Gay")


async def authenticate():
    global crafty_api_token
    crafty_login = os.getenv("CRAFTY_LOGIN")
    crafty_password = os.getenv("CRAFTY_PASSWORD")
    if not crafty_login or not crafty_password:
        logging.error(
            "CRAFTY_LOGIN or CRAFTY_PASSWORD environment variables are not set."
        )
        return
    url = "https://crafty.tessdev.fr/api/v2/auth/login"
    payload = {
        "username": crafty_login,
        "password": crafty_password,
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as response:
            data = await response.json()
            logging.info(f"Authentication response status: {response.status}")
            if response.status == 200:
                crafty_api_token = data["data"]["token"]
                logging.info("Successfully authenticated, new token obtained")
                update_env_file(crafty_api_token)
            else:
                logging.error("Failed to authenticate")
                logging.error(data)


def update_env_file(new_token):
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    with open(env_path, "r") as file:
        lines = file.readlines()

    with open(env_path, "w") as file:
        for line in lines:
            if line.startswith("CRAFTY_API_TOKEN"):
                file.write(f'CRAFTY_API_TOKEN="{new_token}"\n')
            else:
                file.write(line)


async def ensure_authenticated():
    global crafty_api_token
    if not crafty_api_token:
        await authenticate()


async def main():
    global crafty_api_token
    global api_weather
    global tenor_api_key
    global tess_bot_id

    tenor_api_key = os.getenv("TENOR_API_KEY")
    tess_bot_id = os.getenv("TESS_BOT_ID")
    crafty_api_token = os.getenv("CRAFTY_API_TOKEN")
    if crafty_api_token is None:
        logging.error("Crafty API token is not set in the environment variables.")
        logging.info("Attempting to authenticate...")
        await authenticate()  # Correctly using await here

    bot_token = os.getenv("BOT_TOKEN")
    api_weather = os.getenv("OPENWEATHERMAP_API_KEY")
    if bot_token is None or api_weather is None:
        logging.error(
            "Bot token or api_weather is not set in the environment variables."
        )
        return  # Exit the function if the bot token is not set
    # Get the API key from environment variable
    # Use await bot.start(bot_token) instead of bot.run(bot_token)
    await bot.start(bot_token)


if __name__ == "__main__":
    initialize_database()
    asyncio.run(main())
    if os.path.exists("log_once_per_session.txt"):
        os.remove("log_once_per_session.txt")
