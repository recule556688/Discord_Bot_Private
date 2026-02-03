"""Custom checks for Discord commands."""

import discord
from discord import app_commands

from config import ADDITIONAL_ALLOWED_USER_ID


def is_owner():
    async def predicate(interaction: discord.Interaction):
        if interaction.user.id in ADDITIONAL_ALLOWED_USER_ID:
            return True
        if interaction.guild is not None:
            return interaction.user.id == interaction.guild.owner_id
        return False

    return app_commands.check(predicate)
