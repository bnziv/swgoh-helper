import os
import discord
from discord.ext import commands
import helpers
from unidecode import unidecode

db = helpers.db
bot = commands.Bot(command_prefix='?', intents=discord.Intents.all())

@bot.hybrid_group(name='unit', description='Get a unit\'s basic info', fallback="get")
async def unit(ctx, unit):
    queryTags = '''SELECT t.name FROM tags t
    JOIN unit_tags ut ON ut.tag_id = t.tag_id
    JOIN units u ON u.unit_id = ut.unit_id
    WHERE u.name = %s
    '''
    db.cursor.execute(queryTags, (unit,))
    tags = [tag[0] for tag in db.cursor.fetchall()]
    queryUnit = '''SELECT name, description, image_url, unit_id FROM units WHERE name = %s'''
    db.cursor.execute(queryUnit, (unit,))
    unit = db.cursor.fetchone()

    embed = discord.Embed(title=f"{unit[0]}", description=unit[1])
    embed.add_field(name="Tags", value=(", ".join(tags)), inline=False)
    embed.set_thumbnail(url=f"https://game-assets.swgoh.gg/textures/{unit[2]}.png")

    embed.add_field(name="\u200b", value=f"**[Counters](https://swgoh.gg/counters/{unit[3]}/?sort=count)**", inline=True)

    name = unidecode(unit[0]).lower().replace(" ", "-") #Format name for swgoh.gg url
    embed.add_field(name="\u200b", value=f"**[Mods](https://swgoh.gg/units/{name}/best-mods/)**", inline=True)
    embed.color = discord.Color.yellow()

    await ctx.send(embed=embed)
unit.autocomplete("unit")(helpers.unit_autocomplete)

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
abilities.autocomplete("unit")(helpers.unit_autocomplete)


@bot.event
async def on_ready():
    await bot.tree.sync()
    print('Bot started')

bot.run(os.getenv('BOT_TOKEN'))