"""Fun commands: joke, cat, weather."""

import typing
from datetime import datetime, timedelta

import discord
import requests
from discord import app_commands
from discord.ext import commands

from config import CITY, get_api_weather


async def city_autocompletion(
    interaction: discord.Interaction, current: str
) -> typing.List[app_commands.Choice[str]]:
    data = []
    for city in CITY:
        if current.lower() in city.lower():
            data.append(app_commands.Choice(name=city, value=city))
    return data


class Fun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="joke", description="Get a random joke")
    async def joke_slash(
        self, interaction: discord.Interaction, hide_message: bool = True
    ):
        response = requests.get("https://official-joke-api.appspot.com/random_joke")
        data = response.json()
        joke = f"{data['setup']}\n{data['punchline']}"
        await interaction.response.send_message(joke, ephemeral=hide_message)

    @app_commands.command(name="cat", description="Get cute cat images")
    async def cat_slash(
        self,
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
                await interaction.response.send_message(
                    embed=embed, ephemeral=hide_message
                )
            else:
                await interaction.followup.send(
                    embed=embed, ephemeral=hide_message
                )

    @app_commands.command(
        name="weather", description="Get the current weather in a city"
    )
    @app_commands.autocomplete(city=city_autocompletion)
    async def weather_slash(
        self,
        interaction: discord.Interaction,
        city: str,
        forecast: bool = False,
    ):
        api_weather = get_api_weather()
        if forecast:
            base_url = "http://api.openweathermap.org/data/2.5/forecast"
        else:
            base_url = "http://api.openweathermap.org/data/2.5/weather"

        response = requests.get(
            base_url,
            params={"q": city, "appid": api_weather, "units": "metric"},
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
                weather["main"] == "Rain"
                for weather in tomorrow_forecast["weather"]
            )
        else:
            weather_description = data["weather"][0]["description"]
            temperature = data["main"]["temp"]
            weather_icon = data["weather"][0]["icon"]
            will_rain = any(
                weather["main"] == "Rain" for weather in data["weather"]
            )

        embed = discord.Embed(title=f"Weather in {city.title()}")
        embed.add_field(name="Description", value=weather_description, inline=False)
        embed.add_field(name="Temperature", value=f"{temperature}°C", inline=False)
        embed.add_field(
            name="Will it rain?", value="Yes" if will_rain else "No", inline=False
        )
        embed.set_thumbnail(
            url=f"http://openweathermap.org/img/w/{weather_icon}.png"
        )

        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Fun(bot))
