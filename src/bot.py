from backend import dataloader, log
from backend.helpers import HOURLY_LOOP
import asyncio
import os
import discord
from discord.ext import commands, tasks

directory = os.path.dirname(os.path.abspath(__file__))
cogs_directory = os.path.join(directory, 'cogs')
cogs = [file[:-3] for file in os.listdir(cogs_directory) if file.endswith('.py')]

bot = commands.Bot(command_prefix='?', intents=discord.Intents.all())

@bot.event
async def setup_hook():
    for cog in cogs:    
        await bot.load_extension(f"cogs.{cog}")
    await bot.tree.sync()

@bot.event
async def on_ready():
    log("Bot started")
    update_loop.start()

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

@tasks.loop(time=HOURLY_LOOP)
async def update_loop():
    await dataloader.check_version()

bot.run(os.getenv('BOT_TOKEN'))