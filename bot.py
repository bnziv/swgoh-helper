import asyncio
import datetime
import os
import discord
from discord import app_commands
from discord.ext import commands, tasks
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

@bot.hybrid_group(name="allycode", description="Add an allycode to your Discord account", fallback="add")
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
    offset = result['localTimeZoneOffsetMinutes']
    discord_id = ctx.user.id
    query = '''
    INSERT INTO users (allycode, discord_id, name, time_offset) VALUES (%s, %s, %s, %s)
    '''
    db.cursor.execute(query, (allycode, discord_id, name, offset))
    db.connection.commit()
    await ctx.response.send_message(f"**{name}** ({allycode}) is now linked to your Discord account")
    
@allycode.command(name="remove", description="remove an allycode from your Discord account")
async def allycode_remove(ctx, allycode: int):
    """
    Remove an allycode from your Discord account

    Args:
        allycode (int): The allycode of the player
    """
    query = '''
    DELETE FROM users WHERE discord_id = %s
    '''
    db.cursor.execute(query, (allycode, str(ctx.author.id),))
    db.connection.commit()
    if db.cursor.rowcount == 0:
        await ctx.response.send_message("This allycode is not linked to your Discord account")
    else:
        await ctx.response.send_message("This allycode has been removed from your Discord account")
    
    
@allycode.command(name="view", description="list all allycodes linked to your Discord account")
async def view(ctx):
    """
    Get all allycodes linked to your Discord account
    """
    query = '''
    SELECT allycode, name FROM users WHERE discord_id = %s
    '''
    db.cursor.execute(query, (str(ctx.author.id),))
    result = db.cursor.fetchall()
    embed = discord.Embed(title="Your allycodes")
    if len(result) == 0:
        embed.description = "You have no allycodes linked to your Discord account"
    else:
        for allycode, name in result:
            embed.add_field(name=allycode, value=name, inline=False)
    await ctx.send(embed=embed)


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
    
    #All flag
    if all:
        result = fleetpayout.get_all_payouts()
        if len(result) == 0:
            embed.description = "Your fleet shard is empty"
        else:
            for allycode, name, offset in result:
                embed.add_field(
                    name = f"**{name}** ({allycode})",
                    value = f"<t:{helpers.calculate_payout(offset)}:t>"
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
                    value = f"<t:{helpers.calculate_payout(offset)}:t>"
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
        value = f"<t:{helpers.calculate_payout(offset)}:t>"
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
async def on_ready():
    await bot.tree.sync()
    print('Bot started')
    start_notify_payouts.start()

bot.run(os.getenv('BOT_TOKEN'))