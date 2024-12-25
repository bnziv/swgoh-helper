import sys
sys.path.append("..")
import helpers
import discord
from discord import app_commands
from discord.ext import commands, tasks
from datetime import datetime, timedelta, timezone
import asyncio

db = helpers.db

class DailiesEmbed(discord.Embed):
    def __init__(self, title=None, description=None):
        super().__init__(title=title, description=description, color=discord.Color.brand_green())

class Dailies(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def energy_listener(self, discord_id, name, offset, energy_timing):
        embed = DailiesEmbed(description=f"Free energy for **{name}** is available")
        current = int(datetime.now().timestamp())
        user = self.bot.get_user(int(discord_id))
        energy_time = helpers.calculate_reset(offset) + energy_timing
        delay = energy_time - current
        await asyncio.sleep(delay)
        message = await user.send(embed=embed, delete_after=7200)
        await message.add_reaction("✅")
        reminder = None
        try:
            def check(reaction, reactor):
                return (user.id == reactor.id and str(reaction.emoji) == "✅" and reaction.message.id == message.id)
            await self.bot.wait_for("reaction_add", timeout=5400, check=check)
            await message.delete()
        except asyncio.TimeoutError:
            reminder_embed = DailiesEmbed(description=f"30 minutes left to claim free energy")
            reminder = await user.send(embed=reminder_embed, delete_after=1800)
            try:
                await self.bot.wait_for("reaction_add", timeout=1800, check=check)
                await message.delete()
                await reminder.delete()
            except:
                pass

    async def dailies_listener(self, discord_id, name, offset):
        embed = DailiesEmbed(title="Daily Reset", description=f"React to the message if **{name}** has completed dailies")
        current = int(datetime.now().timestamp())
        user = self.bot.get_user(int(discord_id))
        reset_time = helpers.calculate_reset(offset)
        delay = reset_time - current
        await asyncio.sleep(delay)
        message = await user.send(embed=embed, delete_after=86400)
        await message.add_reaction("✅")
        reminder = None
        try:
            def check(reaction, reactor):
                return (user.id == reactor.id and str(reaction.emoji) == "✅" and reaction.message.id == message.id)
            await self.bot.wait_for("reaction_add", timeout=82800, check=check)
            await message.delete()
        except asyncio.TimeoutError:
            reminder_embed = DailiesEmbed(description=f"1 hour left until reset\nReminder for {name} to do dailies")
            reminder = await user.send(embed=reminder_embed, delete_after=3600)
            try:
                await self.bot.wait_for("reaction_add", timeout=3600, check=check)
                await message.delete()
                await reminder.delete()
            except:
                pass
        
    @tasks.loop(hours=24)
    async def start_listeners(self):
        db.cursor.execute("SELECT discord_id, name, time_offset FROM users WHERE notify_energy IS TRUE")
        for user in db.cursor.fetchall():
            asyncio.create_task(self.dailies_listener(*user))
            asyncio.create_task(self.energy_listener(*user, timedelta(hours=12).total_seconds()))
            asyncio.create_task(self.energy_listener(*user, timedelta(hours=18).total_seconds()))
            asyncio.create_task(self.energy_listener(*user, timedelta(hours=21).total_seconds()))

    # @start_listeners.before_loop
    # async def before_start_listeners(self):
    #     now = datetime.now()
    #     next_day = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    #     delay = (next_day - now).total_seconds()
    #     await asyncio.sleep(delay)

    @commands.Cog.listener()
    async def on_ready(self):
        self.start_listeners.start()
        
async def setup(bot):
    await bot.add_cog(Dailies(bot))
        