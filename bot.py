import json
import typing
import discord
import os
import asyncio
import requests
import logging
from discord import app_commands, Embed, ui, ButtonStyle, Colour
from discord.ext import commands, tasks
from dotenv import load_dotenv
from datetime import datetime, timedelta
from dateutil.parser import parse
from Crypto.Cipher import AES
import base64
from clean_log_file import clean_log_file

# Setup logging
logging.basicConfig(level=logging.INFO)


# Function to encrypt JSON data
def encrypt_json(data, key):
    cipher = AES.new(key, AES.MODE_EAX)
    ciphertext, tag = cipher.encrypt_and_digest(json.dumps(data).encode())
    json_val = [
        base64.b64encode(x).decode("utf-8") for x in (cipher.nonce, ciphertext, tag)
    ]
    return json_val


# Function to decrypt JSON data
def decrypt_json(json_val, key):
    nonce, ciphertext, tag = [base64.b64decode(x.encode("utf-8")) for x in json_val]
    cipher = AES.new(key, AES.MODE_EAX, nonce=nonce)
    data = cipher.decrypt_and_verify(ciphertext, tag)
    return json.loads(data)


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

# Create a dictionary to store birthdays
birthdays = {}
# Get the directory of the current script
script_dir = os.path.dirname(os.path.abspath(__file__))
# Join with the relative path
file_path = os.path.join(script_dir, "data", "birthdays.json")

# Load .env file
load_dotenv()
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)


ADDITIONAL_ALLOWED_USER_ID = 766746672964567052  # Replace with the actual user ID

def is_owner():
    def predicate(interaction: discord.Interaction):
        # Check if the user is the server owner
        is_server_owner = interaction.user.id == interaction.guild.owner.id
        # Check if the user is the additional allowed user
        is_additional_user = interaction.user.id == ADDITIONAL_ALLOWED_USER_ID
        # Allow if the user is either the server owner or the additional allowed user
        return is_server_owner or is_additional_user

    return app_commands.check(predicate)

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


# Create a global variable to store the user, message, and time
scheduled_message = {"user": None, "message": "", "time": ""}


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
            "appid": api_key,
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
    data = []

    for name in birthdays.keys():
        if current.lower() in name.lower():
            data.append(app_commands.Choice(name=name, value=name))

    for member in interaction.guild.members:
        if current.lower() in member.name.lower():
            data.append(app_commands.Choice(name=member.name, value=member.name))

    return data


async def action_autocompletion(
    interaction: discord.Interaction, current: str
) -> typing.List[app_commands.Choice[str]]:
    actions = ["add", "delete", "display", "next"]
    data = []

    for action in actions:
        if current.lower() in action.lower():
            data.append(app_commands.Choice(name=action, value=action))

    return data


def load_birthdays():
    with open(file_path, "r") as f:
        return json.load(f)


@bot.tree.command(name="birthday", description="Set your birthday")
@app_commands.autocomplete(name=name_autocompletion)
@app_commands.autocomplete(action=action_autocompletion)
async def birthday_slash(
    interaction: discord.Interaction,
    action: str,
    name: str = None,
    birthdate: str = None,
):
    global birthdays
    if action == "add":
        if name and birthdate:
            birthdate = parse(birthdate).strftime("%d/%m/%Y")
            birthdays = load_birthdays()
            birthdays[name] = birthdate
            with open(file_path, "w") as f:
                json.dump(birthdays, f)
            embed = Embed(
                title="Birthday Added",
                description=f"Added birthday for {name} on {birthdate}",
                color=0x00FF00,
            )
            await interaction.response.send_message(embeds=[embed])
        else:
            embed = Embed(
                title="Error",
                description="You must provide a name and birthdate to add a birthday.",
                color=0xFF0000,
            )
            await interaction.response.send_message(embeds=[embed])
    elif action == "delete":
        if name in birthdays:
            del birthdays[name]
            with open(file_path, "w") as f:
                json.dump(birthdays, f)
            embed = Embed(
                title="Birthday Deleted",
                description=f"Deleted birthday for {name}",
                color=0x00FF00,
            )
            await interaction.response.send_message(embeds=[embed])
        else:
            embed = Embed(
                title="Error",
                description="You must provide a valid name to delete a birthday.",
                color=0xFF0000,
            )
            await interaction.response.send_message(embeds=[embed])
    elif action == "display":
        birthdays = load_birthdays()
        if name:
            if name in birthdays:
                embed = Embed(
                    title=f"Birthday for {name}",
                    description=f"{name}: {birthdays[name]}",
                    color=0x00FF00,
                )
            else:
                embed = Embed(
                    title="No Birthday Found",
                    description=f"No birthday found for {name}.",
                    color=0xFF0000,
                )
        else:
            if birthdays:
                embed = Embed(
                    title="Birthdays",
                    description="\n".join(
                        [
                            f"{name}: {birthdate}"
                            for name, birthdate in birthdays.items()
                        ]
                    ),
                    color=0x00FF00,
                )
            else:
                embed = Embed(
                    title="No Birthdays",
                    description="No birthdays to display.",
                    color=0xFF0000,
                )
        await interaction.response.send_message(embeds=[embed])
    elif action == "next":
        if name:
            birthdays = load_birthdays()
            if name in birthdays:
                birthdate = datetime.strptime(birthdays[name], "%d/%m/%Y")
                now = datetime.now()
                next_birthday = birthdate.replace(year=now.year)
                if now > next_birthday:
                    next_birthday = next_birthday.replace(year=now.year + 1)
                days_left = (next_birthday - now).days
                embed = Embed(
                    title=f"Next Birthday for {name}",
                    description=f"{days_left} days until {name}'s next birthday.",
                    color=0x00FF00,
                )
                await interaction.response.send_message(embeds=[embed])
            else:
                embed = Embed(
                    title="No Birthday Found",
                    description=f"No birthday found for {name}.",
                    color=0xFF0000,
                )
                await interaction.response.send_message(embeds=[embed])
        else:
            embed = Embed(
                title="No Birthdays",
                description="No birthdays to display.",
                color=0xFF0000,
            )
            await interaction.response.send_message(embeds=[embed])


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    message_data = {
        "user": message.author.name,
        "message": message.content,
        "time": message.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        "attachments": [attachment.url for attachment in message.attachments],
        "guild": message.guild.name if message.guild else "Direct Message",
    }

    encrypted_data = encrypt_json(message_data, key)

    with open("data/message_logs.ndjson", "a") as f:
        f.write(json.dumps(encrypted_data) + "\n")

    await bot.process_commands(message)


@bot.event
async def on_message_edit(before, after):
    if before.author == bot.user:
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
    }

    encrypted_data = encrypt_json(edit_data, key)

    with open("data/message_logs.ndjson", "a") as f:
        f.write(json.dumps(encrypted_data) + "\n")


class LogEmbed(ui.View):
    def __init__(self, logs):
        super().__init__()
        self.logs = logs
        self.current_page = 0

    @ui.button(label="Previous", style=ButtonStyle.primary)
    async def previous_button(
        self, interaction: discord.Interaction, button: ui.Button
    ):
        try:
            if self.current_page > 0:
                self.current_page -= 1
                await interaction.response.edit_message(
                    embed=self.get_embed(), view=self
                )
            else:
                await interaction.response.send_message(
                    "You are already on the first page.", ephemeral=True
                )
        except Exception as e:
            logging.error(f"Error in previous_button: {e}")
            await interaction.response.send_message(
                "An error occurred.", ephemeral=True
            )

    @ui.button(label="Next", style=ButtonStyle.primary)
    async def next_button(self, interaction: discord.Interaction, button: ui.Button):
        try:
            if self.current_page < len(self.logs) - 1:
                self.current_page += 1
                await interaction.response.edit_message(
                    embed=self.get_embed(), view=self
                )
            else:
                await interaction.response.send_message(
                    "You are already on the last page.", ephemeral=True
                )
        except Exception as e:
            logging.error(f"Error in next_button: {e}")
            await interaction.response.send_message(
                "An error occurred.", ephemeral=True
            )

    def get_embed(self):
        log = self.logs[self.current_page]
        embed = Embed(title=f"Log {self.current_page + 1}", color=Colour.dark_purple())
        embed.set_thumbnail(
            url="https://cdn.discordapp.com/attachments/1190690414190153750/1242135381592506400/logo.png?ex=664cbc38&is=664b6ab8&hm=2571cd16ba78b4f5f4477d00dde90b04cd675e5c66054deaaade14335c0ded78&"
        )
        embed.set_footer(text="Tess Spy Agency")
        embed.timestamp = datetime.now()
        for k, v in log.items():
            v = str(v)
            while len(v) > 0:
                embed.add_field(name=k, value=v[:1024], inline=False)
                v = v[1024:]
        return embed


@bot.tree.command(
    name="read_logs",
    description="Read the content of the message logs",
)
@is_owner()
async def read_logs_slash(interaction: discord.Interaction, hide_message: bool = False):
    with open("data/message_logs.ndjson", "r") as f:
        logs = f.readlines()

    decrypted_logs = []
    for log in logs:
        try:
            decrypted_log = decrypt_json(json.loads(log), key)
            decrypted_logs.append(decrypted_log)
        except json.JSONDecodeError as e:
            logging.error(f"Error decoding JSON: {e} - Log: {log}")
        except ValueError as e:
            logging.error(f"Error decrypting log: {e} - Log: {log}")

    if decrypted_logs:
        view = LogEmbed(decrypted_logs)
        await interaction.response.send_message(embed=view.get_embed(), view=view, ephemeral=hide_message)
    else:
        await interaction.response.send_message("No valid logs found.", ephemeral=hide_message)


@bot.event
async def on_ready():
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching, name="Watching you in the shower"
        ),
        status=discord.Status.dnd,
    )
    try:
        clean_log_file()
        logging.info("Successfully cleaned the log file.")
    except Exception as e:
        logging.error(f"Failed to clean the log file: {e}")
    logging.info(f"Logged in as {bot.user.name} - {bot.user.id}")
    logging.info(f"{bot.user.name}_BOT is ready to go !")
    check_time.start()
    global start_time
    start_time = datetime.utcnow()
    logging.info(f"Bot started at {start_time}")

    try:
        synced = await bot.tree.sync()
        logging.info(f"Synced {len(synced)} commands")
    except Exception as e:
        logging.error(f"Failed to sync commands: {e}")

    try:
        with open(file_path, "r") as f:
            birthdays = json.load(f)
            logging.info("Loaded birthdays from file.")
    except FileNotFoundError:
        with open(file_path, "w") as f:
            json.dump({}, f)
        logging.info("No birthdays json file found. Starting with an empty dictionary.")


# Use the bot token from .env file
bot_token = os.getenv("BOT_TOKEN")
api_key = os.getenv("OPENWEATHERMAP_API_KEY")
key_str = os.getenv("ENCRYPTION_KEY")
key = base64.b64decode(key_str)
if bot_token is None or api_key is None or key_str is None:
    logging.error(
        "Bot token or api_key or ENCRYPTION_KEY is not set in the environment variables."
    )
else:
    bot.run(bot_token)
