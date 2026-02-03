"""Moderation: banned words, temp bans, on_message, on_member_join."""

import asyncio
import logging

import discord
from discord.ext import commands, tasks
from discord.utils import utcnow
from datetime import timedelta

from config import BANNED_WORDS, WAITING_ROOM_SERVER_ID, WAITING_ROOM_CHANNEL_ID
from database import log_message_to_db, load_excluded_channels
from state import temp_bans, banned_users_roles


class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def cog_load(self):
        self.check_temp_bans.start()

    def cog_unload(self):
        self.check_temp_bans.cancel()

    async def ban_user(self, message, word):
        try:
            member = message.author
            guild = message.guild
            user_id = member.id

            user_roles = [
                role.id for role in member.roles if role.name != "@everyone"
            ]

            if user_id not in banned_users_roles:
                banned_users_roles[user_id] = {}
            banned_users_roles[user_id][guild.id] = user_roles

            logging.info(f"Stored roles for {member.name} in {guild.name}: {user_roles}")

            temp_bans[user_id] = {
                "guild_id": guild.id,
                "guild": guild,
                "expiry": utcnow() + timedelta(minutes=1),
            }

            await guild.ban(
                member,
                reason=f"Used banned word: {word}",
                delete_message_seconds=0,
            )

            waiting_room = self.bot.get_guild(WAITING_ROOM_SERVER_ID)
            if not waiting_room:
                logging.error("Waiting room server not found!")
                return

            try:
                waiting_channel = waiting_room.get_channel(
                    WAITING_ROOM_CHANNEL_ID
                )
                invite = await waiting_channel.create_invite(
                    max_age=0, max_uses=1, unique=True
                )

                await member.send(
                    f"You have been temporarily suspended from {guild.name} for using the banned word: **{word}**\n"
                    f"The suspension will last for 1 minute.\n\n"
                    f"Please join our waiting room server to be notified when your suspension expires: {invite.url}\n\n"
                    f"⚠️ Note: The following words are banned:\n"
                    f"```\n{', '.join(BANNED_WORDS)}```"
                )

                await member.kick(reason=f"Used banned word: {word}")
                await message.delete()

                await message.channel.send(
                    f"🚫 {member.mention} has been temporarily suspended for using the banned word: **{word}**\n"
                    "They will be able to rejoin in 1 minute."
                )

            except discord.Forbidden:
                await message.channel.send(
                    "I don't have permission to perform this action.",
                    delete_after=10,
                )
            except Exception as e:
                logging.error(f"Error in ban_user: {str(e)}")
                await message.channel.send(
                    "An error occurred while processing the suspension.",
                    delete_after=10,
                )

        except Exception as e:
            logging.error(f"Error in ban_user: {str(e)}")

    @tasks.loop(seconds=30)
    async def check_temp_bans(self):
        current_time = utcnow()
        to_unban = []

        for user_id, ban_info in temp_bans.items():
            if current_time >= ban_info["expiry"]:
                to_unban.append((user_id, ban_info))

        for user_id, ban_info in to_unban:
            try:
                guild = ban_info.get("guild") or self.bot.get_guild(
                    ban_info["guild_id"]
                )
                if not guild:
                    logging.error(f"Could not find guild for user {user_id}")
                    continue

                user = discord.Object(id=user_id)

                try:
                    await guild.unban(user, reason="Temporary ban expired")
                    logging.info(
                        f"Successfully unbanned user {user_id} from {guild.name}"
                    )

                    invite_channel = next(
                        (
                            channel
                            for channel in guild.text_channels
                            if channel.permissions_for(
                                guild.me
                            ).create_instant_invite
                        ),
                        None,
                    )

                    if invite_channel:
                        invite = await invite_channel.create_invite(
                            max_age=0,
                            max_uses=1,
                            reason="Temporary ban expired",
                        )

                        try:
                            user_obj = await self.bot.fetch_user(user_id)
                            await user_obj.send(
                                f"Your temporary ban from {guild.name} has expired! "
                                f"You can rejoin using this invite: {invite.url}\n"
                                "This invite will never expire."
                            )
                        except discord.Forbidden:
                            logging.error(
                                f"Could not send DM to user {user_id}"
                            )
                        except Exception as e:
                            logging.error(
                                f"Error sending unban notification: {str(e)}"
                            )

                except discord.NotFound:
                    logging.error(
                        f"User {user_id} was not found or already unbanned from {guild.name}"
                    )
                except discord.Forbidden:
                    logging.error(
                        f"Bot lacks permission to unban user {user_id} from {guild.name}"
                    )
                except Exception as e:
                    logging.error(
                        f"Error unbanning user {user_id} from {guild.name}: {str(e)}"
                    )

                del temp_bans[user_id]

            except Exception as e:
                logging.error(
                    f"Error processing unban for user {user_id}: {str(e)}"
                )

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        message_words = message.content.lower().split()
        for word in message_words:
            if word in [banned.lower() for banned in BANNED_WORDS]:
                await self.ban_user(message, word)
                return

        await self.bot.process_commands(message)

        excluded_channels = load_excluded_channels()
        if message.author == self.bot.user or message.channel.id in excluded_channels:
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
        await self.bot.process_commands(message)

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        excluded_channels = load_excluded_channels()
        if before.author == self.bot.user or before.channel.id in excluded_channels:
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
        await self.bot.process_commands(after)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        user_id = member.id
        guild_id = member.guild.id

        logging.info(
            f"Member joined: {member.name} (ID: {user_id}) in guild {member.guild.name} (ID: {guild_id})"
        )

        if (
            user_id in banned_users_roles
            and guild_id in banned_users_roles[user_id]
        ):
            try:
                stored_role_ids = banned_users_roles[user_id][guild_id]
                roles_to_add = []
                for role_id in stored_role_ids:
                    role = member.guild.get_role(role_id)
                    if role and role < member.guild.me.top_role:
                        roles_to_add.append(role)

                if roles_to_add:
                    await member.add_roles(
                        *roles_to_add,
                        reason="Restoring roles after temporary ban",
                    )
                    role_names = [role.name for role in roles_to_add]
                    logging.info(
                        f"Successfully restored roles for {member.name}: {role_names}"
                    )

                del banned_users_roles[user_id][guild_id]
                if not banned_users_roles[user_id]:
                    del banned_users_roles[user_id]

            except discord.Forbidden as e:
                logging.error(
                    f"Permission error restoring roles for {member.name}: {str(e)}"
                )
            except Exception as e:
                logging.error(
                    f"Error restoring roles for {member.name}: {str(e)}"
                )


async def setup(bot):
    await bot.add_cog(Moderation(bot))
