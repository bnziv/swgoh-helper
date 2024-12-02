import sys
sys.path.append("..")
import helpers
import discord
from discord import app_commands
from discord.ext import commands, tasks
from datetime import datetime, timedelta, timezone
import asyncio

db = helpers.db

class Dailies(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def energy_listener(self, allycode, discord_id, name, offset):
        pass

    async def dailies_listener(self, allycode, discord_id, name, offset):
        embed = discord.Embed(title="Daily Reset", description=f"React to the message if **{name}** has completed dailies")
        current = int(datetime.now().timestamp())
        user = self.bot.get_user(int(discord_id))
        reset_time = helpers.calculate_reset(offset)
        if current > reset_time:
            reset_time += 86400
        delay = reset_time - current
        await asyncio.sleep(abs(delay))
        message = await user.send(embed=embed, delete_after=86400)
        await message.add_reaction("✅")
        reminder = None
        try:
            def check(reaction, reactor):
                return (user.id == reactor.id and str(reaction.emoji) == "✅" and reaction.message.id == message.id)
            await self.bot.wait_for("reaction_add", timeout=82800, check=check)
            await message.delete()
        except asyncio.TimeoutError:
            reminder = await user.send(embed=discord.Embed(description=f"1 hour left until reset\nReminder for {name} to do dailies"), delete_after=3600)
            try:
                await self.bot.wait_for("reaction_add", timeout=3600, check=check)
                await message.delete()
                await reminder.delete()
            except:
                pass
        
    @tasks.loop(hours=24)
    async def start_listeners(self):
        db.cursor.execute("SELECT allycode, discord_id, name, time_offset FROM users WHERE notify_energy IS TRUE")
        for user in db.cursor.fetchall():
            asyncio.create_task(self.energy_listener(*user))
            asyncio.create_task(self.dailies_listener(*user))

    @start_listeners.before_loop
    async def before_start_listeners(self):
        now = datetime.now()
        next_day = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        delay = (next_day - now).total_seconds()
        await asyncio.sleep(delay)

    @commands.Cog.listener()
    async def on_ready(self):
        self.start_listeners.start()
        
async def setup(bot):
    await bot.add_cog(Dailies(bot))
        