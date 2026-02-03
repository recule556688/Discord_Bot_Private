"""Logging commands: manage_logging_channels, read_logs, delete_all_logs, LogEmbed."""

import json
import typing
from datetime import datetime

import discord
from discord import Embed, Interaction, SelectOption, app_commands, ui, ButtonStyle
from discord.ext import commands

from database import (
    get_db_connection,
    load_excluded_channels,
    add_logging_channel,
    remove_logging_channel,
)
from utils.checks import is_owner


async def action_autocomplete(
    interaction: discord.Interaction, current: str
) -> typing.List[app_commands.Choice[str]]:
    choices = ["add", "remove", "list"]
    return [
        app_commands.Choice(name=choice, value=choice)
        for choice in choices
        if current.lower() in choice.lower()
    ]


async def channel_autocomplete(
    interaction: discord.Interaction, current: str
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
            and current.lower()
            in interaction.guild.get_channel(c).name.lower()
        ]
    else:
        return [
            app_commands.Choice(name=channel.name, value=str(channel.id))
            for channel in interaction.guild.text_channels
            if channel.id not in excluded_channels
            and current.lower() in channel.name.lower()
        ]


class LogEmbed(ui.View):
    def __init__(self, logs):
        super().__init__()
        self.logs = logs
        self.current_page = 0
        self.total_pages = (len(logs) + 24) // 25
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

        if len(formatted_log) > 1024:
            formatted_log = formatted_log[:1021] + "..."

        return formatted_log


class LoggingCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
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
        self,
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

            ch = interaction.guild.get_channel(int(channel))
            if ch.id not in channels:
                add_logging_channel(ch.id)
                await interaction.response.send_message(
                    f"Added channel {ch.mention} to the list of channels to exclude from logging.",
                    ephemeral=hide_message,
                )
            else:
                await interaction.response.send_message(
                    f"Channel {ch.mention} is already in the list of channels to exclude from logging.",
                    ephemeral=hide_message,
                )

        elif action == "remove":
            if channel is None:
                await interaction.response.send_message(
                    "Please specify a channel to remove.", ephemeral=True
                )
                return

            ch = interaction.guild.get_channel(int(channel))
            if ch.id in channels:
                remove_logging_channel(ch.id)
                await interaction.response.send_message(
                    f"Removed channel {ch.mention} from the list of channels to exclude from logging.",
                    ephemeral=hide_message,
                )
            else:
                await interaction.response.send_message(
                    f"Channel {ch.mention} is not in the list of channels to exclude from logging.",
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
                    "No channels are excluded from logging.",
                    ephemeral=hide_message,
                )

    @app_commands.command(
        name="read_logs", description="Read the content of the message logs"
    )
    @is_owner()
    async def read_logs_slash(
        self, interaction: discord.Interaction, hide_message: bool = True
    ):
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

    @app_commands.command(
        name="delete_all_logs",
        description="Delete the content of all the message logs",
    )
    @is_owner()
    async def delete_all_logs_slash(
        self, interaction: discord.Interaction, hide_message: bool = True
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


async def setup(bot):
    await bot.add_cog(LoggingCog(bot))
