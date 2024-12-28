from backend import db 
import asyncio
import datetime
import os
import discord
from discord.ext import commands, tasks
from datetime import datetime
import backend.helpers as helpers

directory = os.path.dirname(os.path.abspath(__file__))
cogs_directory = os.path.join(directory, 'cogs')
cogs = [file[:-3] for file in os.listdir(cogs_directory) if file.endswith('.py')]

embedColor = discord.Color.dark_purple()
bot = commands.Bot(command_prefix='?', intents=discord.Intents.all())

@tasks.loop(hours=24)
async def start_notify_payouts():
    #TODO: When bot is deployed, sleep until 12AM UTC and pass the start time to the inner functions
    query = '''SELECT allycode, discord_id, name, time_offset FROM users'''
    db.cursor.execute(query)
    result = db.cursor.fetchall()
    for user in result:
        asyncio.create_task(notify_payout(*user))

# @start_notify_payouts.before_loop
# async def before_start_notify_payouts():
#     now = datetime.now(tz=timezone.utc)
#     start_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
#     if now > start_time:
#         start_time += timedelta(days=1)
#     await asyncio.sleep((start_time - now).total_seconds())

async def notify_payout(allycode, discord_id, name, offset):
    embed = discord.Embed(color=embedColor)
    current = int(datetime.now().timestamp())
    user = bot.get_user(int(discord_id))
    payout_time = helpers.calculate_payout(offset)
    notify_time = payout_time - 3600
    if current >= notify_time:
        delay = 0
    else:
        delay = notify_time - current
    await asyncio.sleep(delay)
    embed.description = f"Fleet payout for **{name}** ({allycode}) is <t:{payout_time}:R>\nSending alerts for next available battle until payout"
    start_message = await user.send(embed=embed)
    asyncio.create_task(rank_listener(allycode, discord_id, name, payout_time, start_message))

async def rank_listener(allycode, discord_id, name, payout_time, start_message):
    next_battle_message = warning_message = None
    embed = discord.Embed(color=embedColor)
    current_rank = helpers.get_player_rank(allycode=allycode)
    user = bot.get_user(int(discord_id))
    battles = 0
    while datetime.now().timestamp() < payout_time:
        new_rank = helpers.get_player_rank(allycode=allycode)
        if new_rank < current_rank:
            battles += 1
            current_rank = new_rank
            if datetime.now().timestamp() + 590 < payout_time and battles < 5: #Sufficient time for another battle
                if next_battle_message:
                    await next_battle_message.edit(embed=discord.Embed(description=f"{name}'s next battle is available in <t:{int(datetime.now().timestamp() + 590)}:R>", color=embedColor))
                await asyncio.sleep(590)
                embed.description = f"{name}'s next battle is available"

                if next_battle_message:
                    await next_battle_message.delete()
                next_battle_message = await user.send(embed=embed)
        
        if not warning_message and datetime.now().timestamp() + 90 >= payout_time: #90 seconds before payout
            warning_message = await user.send(embed=discord.Embed(description=f"{name}'s payout is soon", color=embedColor))

        await asyncio.sleep(3)
    
    if warning_message:
        await warning_message.delete()
    if next_battle_message:
        await next_battle_message.delete()
    embed = discord.Embed(title=f"**{name}** finished at rank {current_rank}", timestamp=datetime.now(), color=embedColor)
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

@bot.tree.command(name="update", description="(Admin) Update commands")
@commands.is_owner()
async def update(interaction: discord.Interaction):
    for cog in cogs:
        await bot.reload_extension(f"cogs.{cog}")
    await interaction.response.send_message("Updated", delete_after=3)

@bot.tree.command(name="clear", description="(Admin) Clear the bot's last messages")
@commands.is_owner()
async def clear(interaction: discord.Interaction, amount: int):
    await interaction.response.send_message("Deleting messages...", ephemeral=True)
    messages = interaction.channel.history(limit=200)
    bot_messages = [msg async for msg in messages if msg.author == bot.user]

    for msg in bot_messages[:amount]:
        await msg.delete()
        await asyncio.sleep(1)

    await interaction.edit_original_response(content=f"Done")

bot.run(os.getenv('BOT_TOKEN'))