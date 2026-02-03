"""Info commands: server_stats, avatar, user_info, uptime."""

from datetime import datetime

import discord
from discord import app_commands
from discord.ext import commands


class Info(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="server_stats", description="Display server statistics")
    async def server_stats_slash(
        self, interaction: discord.Interaction, hide_message: bool = True
    ):
        guild = interaction.guild
        member_count = guild.member_count
        text_channels = len(guild.text_channels)
        voice_channels = len(guild.voice_channels)
        role_count = len(guild.roles)

        embed = discord.Embed(
            title="Server Statistics", color=discord.Color.dark_purple()
        )
        embed.add_field(name="Members:", value=str(member_count), inline=False)
        embed.add_field(name="Text Channels:", value=str(text_channels), inline=False)
        embed.add_field(name="Voice Channels:", value=str(voice_channels), inline=False)
        embed.add_field(name="Roles:", value=str(role_count), inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=hide_message)

    @app_commands.command(name="avatar", description="Display the avatar of a user")
    async def avatar_slash(
        self,
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

    @app_commands.command(name="user_info", description="Display information about a user")
    async def user_info_slash(
        self,
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
            value=user.joined_at.strftime("%Y-%m-%d %H:%M:%S")
            if user.joined_at
            else "N/A",
            inline=False,
        )
        embed.add_field(name="Highest Role:", value=user.top_role.name, inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=hide_message)

    @app_commands.command(name="uptime", description="Display the bot's uptime")
    async def uptime_slash(
        self, interaction: discord.Interaction, hide_message: bool = True
    ):
        start_time = getattr(self.bot, "start_time", datetime.utcnow())
        uptime = datetime.utcnow() - start_time
        hours, remainder = divmod(int(uptime.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        days, hours = divmod(hours, 24)

        embed = discord.Embed(title="Uptime", color=discord.Color.dark_purple())
        embed.add_field(
            name="Uptime:",
            value=f"{days}d: {hours}h: {minutes}m: {seconds}s",
            inline=False,
        )

        await interaction.response.send_message(embed=embed, ephemeral=hide_message)


async def setup(bot):
    await bot.add_cog(Info(bot))
