import os
import discord
from discord import app_commands
from discord.ext import commands
import helpers
from unidecode import unidecode
import re

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
    SELECT a.name, a.description, ua.ability_id, a.image_url FROM abilities a
    JOIN unit_abilities ua ON ua.ability_id = a.skill_id
    JOIN units u on u.unit_id = ua.unit_id
    WHERE u.name = %s
    ORDER BY CASE 
        WHEN ua.ability_id LIKE 'basic%%' THEN 1
        WHEN ua.ability_id LIKE 'special%%' THEN 2
        WHEN ua.ability_id LIKE 'leader%%' THEN 3
        WHEN ua.ability_id LIKE 'unique%%' AND ua.ability_id NOT LIKE '%%GALACTICLEGEND%%' THEN 4
        ELSE 5
    END, ua.ability_id;
    '''
    db.cursor.execute(queryAbilities, (unit,))
    abilities = db.cursor.fetchall()
    embeds = []
    for ability in abilities:
        title = ability[2].capitalize().split('skill')[0]
        if title == "Hardware":
            title = "Reinforcement"
        description = ability[1].replace(r'\n', '\n')
        description = re.sub(r'\[c\]\[.*?\]|\[-\]\[/c\]', '**', description)
        embed = discord.Embed(title=f"{unit}\n{title} - {ability[0]}", description=description)
        embed.set_thumbnail(url=f"https://game-assets.swgoh.gg/textures/{ability[3]}.png")
        embeds.append(embed)
    await ctx.send(embed=embeds[0], view=helpers.EmbedPages(embeds))
abilities.autocomplete("unit")(helpers.unit_autocomplete)

@unit.command(name="tags", description="Get all unit's with a specific tag")
async def tags(ctx, tag):
    queryTags = '''SELECT u.name FROM tags t
    JOIN unit_tags ut on ut.tag_id = t.tag_id
    JOIN units u on u.unit_id = ut.unit_id
    WHERE t.name = %s
    ORDER BY u.name;
    '''
    db.cursor.execute(queryTags, (tag,))
    units = db.cursor.fetchall()
    embed = discord.Embed(title=f"Units with {tag} tag", description="\n".join([unit[0] for unit in units]))
    #TODO: Add each unit's tags
    await ctx.send(embed=embed)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print('Bot started')

bot.run(os.getenv('BOT_TOKEN'))