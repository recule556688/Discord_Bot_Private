"""DM commands: dm, cancel_dm, and scheduled messages task."""

import asyncio
import logging
from datetime import datetime

import discord
from discord import app_commands
from discord.ext import commands, tasks


class Dm(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.scheduled_message = {"user": None, "message": "", "time": ""}

    def cog_load(self):
        self.check_time.start()

    def cog_unload(self):
        self.check_time.cancel()

    @tasks.loop(seconds=10)
    async def check_time(self):
        if self.scheduled_message["user"] is not None:
            now = datetime.now()
            scheduled_time = datetime.strptime(
                self.scheduled_message["time"], "%Y-%m-%d %Hh%M"
            )
            if now >= scheduled_time:
                try:
                    await self.scheduled_message["user"].send(
                        self.scheduled_message["message"]
                    )
                    logging.info(
                        f"Successfully sent message to {self.scheduled_message['user'].name}."
                    )
                    self.scheduled_message = {"user": None, "message": "", "time": ""}
                except discord.Forbidden:
                    logging.error(
                        f"Failed to send a DM to {self.scheduled_message['user'].name}. "
                        "They might have DMs disabled or the bot doesn't share a server with them."
                    )

    @app_commands.command(name="dm", description="Send a DM to a user")
    async def dm_slash(
        self,
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
            self.scheduled_message["user"] = user
            self.scheduled_message["message"] = message
            self.scheduled_message["time"] = time
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
                        content=f"Failed to send a DM to {user.name}. They might have DMs disabled or the bot doesn't share a server with them or they are not in the server.",
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

    @app_commands.command(name="cancel_dm", description="Cancel a scheduled DM")
    async def cancel_dm_slash(self, interaction: discord.Interaction):
        if self.scheduled_message["user"] is not None:
            self.scheduled_message = {"user": None, "message": "", "time": ""}
            await interaction.response.send_message(
                "Scheduled message cancelled.", ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "No message is currently scheduled.", ephemeral=True
            )


async def setup(bot):
    await bot.add_cog(Dm(bot))
