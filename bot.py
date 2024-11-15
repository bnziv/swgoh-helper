import os
import discord
from discord.ext import commands
from database import Database

db = Database()
bot = commands.Bot(command_prefix='?', intents=discord.Intents.all())

@bot.hybrid_group(name='unit', description='get unit', fallback="get")
async def unit(ctx, unit):
    query = '''SELECT t.name FROM tags t
    JOIN unit_tags ut ON ut.tag_id = t.tag_id
    JOIN units u ON u.unit_id = ut.unit_id
    WHERE u.name = %s
    '''
    db.cursor.execute(query, (unit,))
    tags = db.cursor.fetchall()
    if tags:
        await ctx.send(tags[0])

@unit.command(name="abilities", description="get unit's abilities")
async def abilities(ctx, unit):
    queryAbilities = '''
    SELECT a.name, a.description FROM abilities a
    JOIN unit_abilities ua ON ua.ability_id = a.skill_id
    JOIN units u on u.unit_id = ua.unit_id
    WHERE u.name = %s
    '''
    db.cursor.execute(queryAbilities, (unit,))
    abilities = db.cursor.fetchall()[0]
    await ctx.send(f"{abilities[0]}\n{abilities[1]}")


@bot.event
async def on_ready():
    await bot.tree.sync()
    print('Bot started')

bot.run(os.getenv('BOT_TOKEN'))