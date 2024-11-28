import sys
sys.path.append("..")
import helpers
from unidecode import unidecode
import re
import discord
from discord import app_commands
from discord.ext import commands

db = helpers.db

class Unit(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    unit = app_commands.Group(name="unit", description="Unit commands")

    @unit.command(name="get", description="Get a unit's basic info")
    async def get(self, interaction: discord.Interaction, unit: str):
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

        await interaction.response.send_message(embed=embed)
    get.autocomplete("unit")(helpers.unit_autocomplete)

    @unit.command(name="abilities", description="Get a unit's abilities")
    async def abilities(self, interaction: discord.Interaction, unit: str):
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
        await interaction.response.send_message(embed=embeds[0], view=helpers.EmbedPages(embeds))
    abilities.autocomplete("unit")(helpers.unit_autocomplete)

    @unit.command(name="tags", description="Get all units with a specific tag")
    async def tags(self, interaction: discord.Interaction, tag: str):
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
        await interaction.response.send_message(embed=embed)
    tags.autocomplete("tag")(helpers.tag_autocomplete)

async def setup(bot):
    await bot.add_cog(Unit(bot))