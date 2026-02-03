"""Birthday command and related autocompletes."""

import logging
import typing
from datetime import datetime

import discord
from discord import Embed, Colour, app_commands
from discord.ext import commands
from dateutil.parser import parse

from database import (
    load_birthdays_from_db,
    save_birthday_to_db,
    delete_birthday_from_db,
)


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

    return data[:25]


async def action_autocompletion(
    interaction: discord.Interaction, current: str
) -> typing.List[app_commands.Choice[str]]:
    actions = ["add", "delete", "display", "next"]
    data = []
    for action in actions:
        if current.lower() in action.lower():
            data.append(app_commands.Choice(name=action, value=action))
    return data


class Birthday(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="birthday", description="Set your birthday")
    @app_commands.describe(
        action="Add, delete, display, or get the number of days before the next birthday"
    )
    @app_commands.autocomplete(name=name_autocompletion)
    @app_commands.autocomplete(action=action_autocompletion)
    async def birthday_slash(
        self,
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
                        embed = Embed(title="📅 Birthdays", color=Colour.blue())
                        for n, bd in birthdays.items():
                            embed.add_field(name=n, value=bd, inline=False)
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
                        birthdate = datetime.strptime(
                            birthdays[name], "%d-%m-%Y"
                        )
                        now = datetime.now()
                        next_birthday = birthdate.replace(year=now.year)
                        if now > next_birthday:
                            next_birthday = next_birthday.replace(
                                year=now.year + 1
                            )
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


async def setup(bot):
    await bot.add_cog(Birthday(bot))
