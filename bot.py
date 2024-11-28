import asyncio
import datetime
import os
import discord
from discord.ext import commands, tasks
from datetime import datetime
import helpers

cogs = []
for file in os.listdir('./cogs'):
    if file.endswith('.py'):
        cogs.append(file[:-3])

comlink = helpers.comlink
db = helpers.db
fleetpayout = helpers.fleetpayout

bot = commands.Bot(command_prefix='?', intents=discord.Intents.all())

@tasks.loop(hours=24)
async def start_notify_payouts():
    #TODO: When bot is deployed, sleep until 12AM UTC and pass the start time to the inner functions
    query = '''SELECT allycode, discord_id, name, time_offset FROM users'''
    db.cursor.execute(query)
    result = db.cursor.fetchall()
    for user in result:
        asyncio.create_task(notify_payout(*user))
        
async def notify_payout(allycode, discord_id, name, offset):
    embed = discord.Embed()
    current = int(datetime.now().timestamp())
    user = bot.get_user(int(discord_id))
    payout_time = helpers.calculate_payout(offset)
    notify_time = payout_time - 3600
    if current >= payout_time:
        delay = payout_time - current + 86400 - 3600
    elif current >= notify_time:
        delay = 0
    else:
        delay = notify_time - current
    await asyncio.sleep(delay)
    embed.description = f"Fleet payout for **{name}** ({allycode}) is <t:{payout_time}:R>\nSending alerts for next battle availablity until payout"
    start_message = await user.send(embed=embed)
    asyncio.create_task(rank_listener(allycode, discord_id, name, payout_time, start_message))

async def rank_listener(allycode, discord_id, name, payout_time, start_message):
    next_battle_message = warning_message = None
    embed = discord.Embed()
    current_rank = comlink.get_player_arena(allycode=allycode, player_details_only=True)['pvpProfile'][1]['rank']
    user = bot.get_user(int(discord_id))
    battles = 0
    while datetime.now().timestamp() < payout_time and battles < 5:
        new_rank = comlink.get_player_arena(allycode=allycode, player_details_only=True)['pvpProfile'][1]['rank']
        if new_rank < current_rank:
            battles += 1
            current_rank = new_rank
            if datetime.now().timestamp() + 590 < payout_time: #Sufficient time for another battle
                await asyncio.sleep(590)
                embed.description = f"{name}'s next battle is available"

                if next_battle_message:
                    await next_battle_message.delete()
                next_battle_message = await user.send(embed=embed)
        
        if not warning_message and datetime.now().timestamp() + 90 >= payout_time: #90 seconds before payout
            warning_message = await user.send(embed=discord.Embed(description=f"{name}'s payout is soon"))

        await asyncio.sleep(3)
    
    if warning_message:
        await warning_message.delete()
    if next_battle_message:
        await next_battle_message.delete()
    embed = discord.Embed(title=f"**{name}** finished at rank {current_rank}", timestamp=datetime.now())
    await start_message.edit(embed=embed)

@bot.event
async def setup_hook():
    for cog in cogs:    
        await bot.load_extension(f"cogs.{cog}")
    await bot.tree.sync()

@bot.event
async def on_ready():
    print('Bot started')
    start_notify_payouts.start()

@bot.tree.command(name="update", description="Update commands")
@commands.is_owner()
async def update(interaction: discord.Interaction):
    for cog in cogs:
        await bot.reload_extension(f"cogs.{cog}")
    await interaction.response.send_message("Cogs loaded")
    await asyncio.sleep(3)
    await interaction.delete_original_response()

bot.run(os.getenv('BOT_TOKEN'))