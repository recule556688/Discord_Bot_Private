"""Admin commands: addrole, ping, owner, clear, force_unban_all, check_stored_roles."""

import logging

import discord
from discord import app_commands
from discord.ext import commands

from config import WAITING_ROOM_SERVER_ID
from database import get_db_connection
from utils.checks import is_owner

from state import banned_users_roles


class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="addrole", description="Assign yourself a specific role by its ID")
    async def add_role_slash(self, interaction: discord.Interaction, role_id: discord.Role):
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

    @app_commands.command(name="ping", description="Returns the bot's latency")
    async def ping_slash(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            f"Pong! {round(self.bot.latency * 1000)}ms", ephemeral=True
        )

    @app_commands.command(name="owner", description="This command is only for the owner of the server")
    @is_owner()
    async def owner_slash(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            f"Hello, {interaction.user.mention} (:", ephemeral=True
        )

    @app_commands.command(name="clear", description="Clear messages from the channel")
    @app_commands.describe(amount="The number of messages to delete")
    async def clear(
        self, interaction: discord.Interaction, amount: int, ephemeral: bool = True
    ):
        if amount < 1:
            await interaction.response.send_message(
                "Please specify a positive number of messages to delete.", ephemeral=True
            )
            return
        await interaction.response.defer(ephemeral=ephemeral)
        await interaction.channel.purge(limit=amount)
        await interaction.followup.send(
            f"Cleared {amount} messages.", ephemeral=ephemeral
        )

    @app_commands.command(
        name="force_unban_all",
        description="Force unban a user from all servers and send invites (Admin only)",
    )
    @is_owner()
    async def force_unban_all_slash(self, interaction: discord.Interaction, user_id: str):
        try:
            try:
                user_id = int(user_id)
            except ValueError:
                await interaction.response.send_message(
                    "Please provide a valid user ID (numbers only).", ephemeral=True
                )
                return

            try:
                user = await self.bot.fetch_user(user_id)
            except discord.NotFound:
                await interaction.response.send_message(
                    f"Could not find user with ID {user_id}.", ephemeral=True
                )
                return

            await interaction.response.send_message(
                "Processing unban across all servers...", ephemeral=True
            )

            results = []
            for guild in self.bot.guilds:
                try:
                    await guild.unban(user, reason="Manual unban by bot owner")
                    try:
                        invite_channel = next(
                            (
                                channel
                                for channel in guild.text_channels
                                if channel.permissions_for(guild.me).create_instant_invite
                            ),
                            None,
                        )
                        if invite_channel:
                            invite = await invite_channel.create_invite(
                                max_age=0, max_uses=1, reason="Manual unban invite"
                            )
                            results.append(
                                f"✅ Unbanned from {guild.name} - Invite: {invite.url}"
                            )
                        else:
                            results.append(
                                f"⚠️ Unbanned from {guild.name} but couldn't create invite (no suitable channel)"
                            )
                    except discord.Forbidden:
                        results.append(
                            f"⚠️ Unbanned from {guild.name} but couldn't create invite (no permission)"
                        )
                except discord.NotFound:
                    results.append(f"ℹ️ Not banned in {guild.name}")
                except discord.Forbidden:
                    results.append(
                        f"❌ Failed to unban from {guild.name} (no permission)"
                    )
                except Exception as e:
                    results.append(f"❌ Error in {guild.name}: {str(e)}")

            result_message = "\n".join(results)
            await interaction.followup.send(
                f"Unban results for {user.name} ({user_id}):\n```\n{result_message}\n```",
                ephemeral=True,
            )

            try:
                invites = "\n".join([r for r in results if "Invite:" in r])
                if invites:
                    await user.send(
                        f"You have been unbanned from multiple servers. Here are your invites:\n```\n{invites}\n```\n"
                        "Each invite can only be used once."
                    )
            except discord.Forbidden:
                await interaction.followup.send(
                    "Could not DM the invites to the user. Please copy them from above.",
                    ephemeral=True,
                )
        except Exception as e:
            await interaction.followup.send(
                f"An unexpected error occurred: {str(e)}", ephemeral=True
            )
            logging.error(f"Error in force_unban_all: {str(e)}")

    @app_commands.command(
        name="check_stored_roles",
        description="Check stored roles for a user (Admin only)",
    )
    @is_owner()
    async def check_stored_roles(self, interaction: discord.Interaction, user_id: str):
        try:
            user_id = int(user_id)
            if user_id in banned_users_roles:
                roles_info = banned_users_roles[user_id]
                await interaction.response.send_message(
                    f"Stored roles for user {user_id}:\n```\n{roles_info}\n```",
                    ephemeral=True,
                )
            else:
                await interaction.response.send_message(
                    f"No stored roles found for user {user_id}", ephemeral=True
                )
        except ValueError:
            await interaction.response.send_message(
                "Please provide a valid user ID (numbers only)", ephemeral=True
            )


async def setup(bot):
    await bot.add_cog(Admin(bot))
