from backend import db, log
import backend.helpers as helpers
from datetime import datetime
import discord
from discord.ext import commands, tasks
import asyncio

class PayoutEmbed(discord.Embed):
    def __init__(self, title=None, description=None):
        super().__init__(title=title, description=description, color=discord.Color.dark_purple())

class Payouts(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @tasks.loop(time=helpers.DAILY_LOOP)
    async def start_notify_payouts(self):
        query = '''SELECT allycode, discord_id, name, time_offset FROM linked_accounts WHERE notify_payout IS TRUE'''
        result = await db.fetch(query)
        for row in result:
            user = (row['allycode'], row['discord_id'], row['name'], row['time_offset'])
            asyncio.create_task(self.notify_payout(*user))

    async def notify_payout(self, allycode, discord_id, name, offset):
        embed = PayoutEmbed()
        current = int(datetime.now().timestamp())
        payout_time = helpers.calculate_payout(offset)
        notify_time = payout_time - 3600
        if current >= notify_time:
            delay = 0
        else:
            delay = notify_time - current
        log(f"Notify payout for {allycode} in {delay} seconds/{datetime.fromtimestamp(notify_time).strftime('%H:%M:%S')}")
        await asyncio.sleep(delay)
        embed.description = f"Fleet payout for **{name}** ({allycode}) is <t:{payout_time}:R>\nSending alerts for next available battle until payout"
        start_message = await helpers.send_dm(self.bot, discord_id, embed)
        if not start_message:
            return
        asyncio.create_task(self.rank_listener(allycode, discord_id, name, payout_time, start_message))

    async def rank_listener(self, allycode, discord_id, name, payout_time, start_message):
        next_battle_message = warning_message = None
        embed = PayoutEmbed()
        current_rank = await helpers.get_player_rank(allycode=allycode)
        battles = 0
        while datetime.now().timestamp() < payout_time:
            new_rank = await helpers.get_player_rank(allycode=allycode)
            if new_rank < current_rank:
                battles += 1
                current_rank = new_rank
                if datetime.now().timestamp() + 590 < payout_time and battles < 5: #Sufficient time for another battle
                    if next_battle_message:
                        description = f"{name}'s next battle is available in <t:{int(datetime.now().timestamp() + 590)}:R>"
                        await next_battle_message.edit(embed=PayoutEmbed(description=description))
                    await asyncio.sleep(590)
                    embed.description = f"{name}'s next battle is available"

                    if next_battle_message:
                        await next_battle_message.delete()
                    next_battle_message = await helpers.send_dm(self.bot, discord_id, embed)
            
            if not warning_message and datetime.now().timestamp() + 90 >= payout_time: #90 seconds before payout
                description = f"{name}'s payout is soon"
                warning_embed = PayoutEmbed(description=description)
                warning_message = await helpers.send_dm(self.bot, discord_id, warning_embed)

            await asyncio.sleep(3)
        
        if warning_message:
            await warning_message.delete()
        if next_battle_message:
            await next_battle_message.delete()
        
        title = f"**{name}** finished at rank {current_rank}"
        embed = PayoutEmbed(title=title)
        embed.timestamp = datetime.now()
        await start_message.edit(embed=embed)
    
    @commands.Cog.listener()
    async def on_ready(self):
        self.start_notify_payouts.start()

async def setup(bot):
    await bot.add_cog(Payouts(bot))