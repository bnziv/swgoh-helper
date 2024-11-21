import datetime
import os
import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timedelta
import pytz
from swgoh_comlink import SwgohComlink
import helpers
from unidecode import unidecode
import re
from queries import Queries

queries = Queries()
comlink = SwgohComlink()
db = helpers.db
fleetpayout = helpers.fleetpayout
bot = commands.Bot(command_prefix='?', intents=discord.Intents.all())

@bot.hybrid_group(name="unit", description="Get a unit's basic info", fallback="get")
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
        WHEN ua.ability_id LIKE 'ultimate%%' THEN 6
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
        elif title.startswith("Ultimate"):
            title = "Ultimate"
        description = ability[1].replace(r'\n', '\n')
        description = re.sub(r'\[c\]\[.*?\]|\[-\]\[/c\]', '**', description)
        embed = discord.Embed(title=f"{unit}\n{title} - {ability[0]}", description=description)
        embed.set_thumbnail(url=f"https://game-assets.swgoh.gg/textures/{ability[3]}.png")
        embeds.append(embed)
        #TODO: Add ability iszeta, isomicron
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

@bot.tree.command(name="allycode")
async def allycode(ctx, allycode: int):
    """
    Add an allycode to your Discord account
    
    Args:
        allycode (int): The allycode of the player
    """

    embed = discord.Embed()
    checkQuery = '''
    SELECT * FROM users WHERE allycode = %s
    '''
    db.cursor.execute(checkQuery, (allycode,))
    result = db.cursor.fetchall()
    if len(result) != 0:
        embed.description = "This allycode is already linked to a Discord account"
        await ctx.response.send_message(embed=embed)
        return
    
    result = helpers.allycode_check(allycode)
    if type(result) == str:
        embed.description = result
        await ctx.response.send_message(embed=embed)
        return

    #TODO: Add confirmation
    name = result['name']
    discord_id = ctx.user.id
    query = '''
    INSERT INTO users (allycode, discord_id) VALUES (%s, %s)
    '''
    db.cursor.execute(query, (allycode, discord_id))
    db.connection.commit()
    await ctx.response.send_message(f"**{name}** ({allycode}) is now linked to your Discord account")


@bot.hybrid_group(name="fleet", description="Get a player's fleet payout time", fallback="get")
async def fleet(ctx, allycode: int = None, name: str = None, all: bool = False):
    """
    Get player's fleet payout time

    Args:
        allycode (int): The allycode of the player
        name (str): The name of the player (if they've been added to your shard)
        all (bool): Get all players' fleet payout times in your shard
    """
    embed = discord.Embed(title="Fleet Payout Time")
    if allycode is None and name is None and not all:
        embed.description = "Please provide an allycode or name\nNames will only work if they've been added to your shard"
        await ctx.send(embed=embed)
        return
    
    def calculate_payout(offset):
        payout = datetime.now(pytz.utc).replace(hour=19, minute=0, second=0, microsecond=0) - timedelta(minutes=offset)
        return f"<t:%d:t>" % int(payout.timestamp())
    
    #All flag
    if all:
        result = fleetpayout.get_all_payouts()
        if len(result) == 0:
            embed.description = "Your fleet shard is empty"
        else:
            for allycode, name, offset in result:
                embed.add_field(
                    name = f"**{name}** ({allycode})",
                    value = calculate_payout(offset)
                    )
        await ctx.send(embed=embed)
        return
    
    #Name provided
    if name:
        result = fleetpayout.get_payout(name=name)
        if len(result) == 0:
            embed.description = f"'{name}' could not be found in your fleet shard"
        else:
            for allycode, name, offset in result:
                embed.add_field(
                    name = f"**{name}** ({allycode})",
                    value = calculate_payout(offset)
                    )
        await ctx.send(embed=embed)
        return
    
    #Allycode provided
    result = fleetpayout.get_payout(allycode=allycode)
    if len(result) != 0:
        name = result[0][1]
        offset = result[0][2]
    else:
        result = helpers.allycode_check(allycode)
        if type(result) == str:
            embed.description = result
            await ctx.send(embed=embed)
            return
        name = result['name']
        offset = result['localTimeZoneOffsetMinutes']
        embed.description = "(This player is not in your fleet shard)"
    embed.add_field(
        name = f"**{name}** ({allycode})",
        value = calculate_payout(offset)
        )
    await ctx.send(embed=embed)
    

@fleet.command(name="add")
async def add(ctx, allycode: int):
    """
    Add a player to your fleet shard
    
    Args:
        allycode (int): The allycode of the player
    """
    embed = discord.Embed()
    result = helpers.allycode_check(allycode)
    if type(result) == str:
        embed.description = result
        await ctx.send(embed=embed)
        return
    name = result['name']
    offset = result['localTimeZoneOffsetMinutes']
    db.cursor.execute('''SELECT allycode from users WHERE discord_id = %s''', (str(ctx.author.id),))
    result = db.cursor.fetchall()
    if len(result) == 0:
        embed.description = "Your Discord account is not linked to an allycode"
        await ctx.send(embed=embed)
    else:
        account_allycode = result[0][0]
        fleetpayout.add_player(allycode, name, offset, account_allycode)
        embed.description = f"**{name}** ({allycode}) has been added to your fleet shard"
    await ctx.send(embed=embed)

@fleet.command(name="remove")
async def remove(ctx, allycode: int):
    """
    Remove a player from your fleet shard
    
    Args:
        allycode (int): The allycode of the player
    """
    embed = discord.Embed()
    if len(str(allycode)) != 9:
        embed.description = "Allycode must be 9 digits long"
        await ctx.send(embed=embed)
        return
    
    if fleetpayout.remove_player(allycode):
        embed.description = f"**{allycode}** has been removed from your fleet shard"
    else:
        embed.description = f"**{allycode}** could not be found in your fleet shard"
    await ctx.send(embed=embed)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print('Bot started')

bot.run(os.getenv('BOT_TOKEN'))