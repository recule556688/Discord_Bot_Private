"""Crafty control commands and update_servers task."""

import logging
import os
import typing

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands, tasks

from config import get_crafty_api_token
from crafty_auth import authenticate


# Global variable for server list (used by autocomplete)
servers = []


async def crafty_action_autocompletion(
    interaction: discord.Interaction, current: str
) -> typing.List[app_commands.Choice[str]]:
    valid_actions = [
        "start_server",
        "stop_server",
        "restart_server",
        "backup_server",
    ]
    return [
        app_commands.Choice(name=action, value=action)
        for action in valid_actions
        if current.lower() in action.lower()
    ]


async def server_uuid_autocompletion(
    interaction: discord.Interaction, current: str
) -> typing.List[app_commands.Choice[str]]:
    filtered = [
        server
        for server in servers
        if current.lower() in server["uuid"].lower()
        or current.lower() in server["name"].lower()
    ]
    return [
        app_commands.Choice(
            name=f"{server['name']} ({server['uuid']})",
            value=server["uuid"],
        )
        for server in filtered[:25]
    ]


class Crafty(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def cog_load(self):
        self.update_servers.start()

    def cog_unload(self):
        self.update_servers.cancel()

    @tasks.loop(seconds=10)
    async def update_servers(self):
        global servers
        url = "https://crafty.tessdev.fr/api/v2/servers"
        token = get_crafty_api_token()
        headers = {"Authorization": f"Bearer {token}"}

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                data = await response.json()
                if response.status == 200:
                    servers = [
                        {
                            "uuid": server["server_id"],
                            "name": server["server_name"],
                        }
                        for server in data.get("data", [])
                    ]
                    if not os.path.exists("log_once_per_session.txt"):
                        logging.info("Successfully fetched server data.")
                        with open("log_once_per_session.txt", "w") as f:
                            f.write("Logged")
                else:
                    logging.error("Failed to fetch server data.")
                    logging.error("Attempting to re-authenticate...")
                    await authenticate()

    @update_servers.before_loop
    async def before_update_servers(self):
        await self.bot.wait_until_ready()

    @app_commands.command(
        name="crafty_control",
        description="Perform an action on a server",
    )
    @app_commands.autocomplete(action=crafty_action_autocompletion)
    @app_commands.autocomplete(server_uuid=server_uuid_autocompletion)
    async def server_action_slash(
        self,
        interaction: discord.Interaction,
        server_uuid: str,
        action: str,
        hide_message: bool = True,
    ):
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

        url = f"https://crafty.tessdev.fr/api/v2/servers/{server_uuid}/action/{action}"
        token = get_crafty_api_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers) as response:
                data = await response.json()
                if response.status == 200 and data.get("status") == "ok":
                    message = "Action performed successfully."
                    if "new_server_id" in data.get("data", {}):
                        message += (
                            f" New server ID: {data['data']['new_server_id']}"
                        )
                    await interaction.response.send_message(
                        message, ephemeral=hide_message
                    )
                else:
                    await interaction.response.send_message(
                        "Failed to perform the action on the server.",
                        ephemeral=hide_message,
                    )


async def setup(bot):
    await bot.add_cog(Crafty(bot))
