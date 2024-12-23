from datetime import datetime
import sys
sys.path.append('..')
import helpers
import discord
from discord import app_commands
from discord.ext import commands

roster = helpers.roster
dataloader = helpers.dataloader
db = helpers.db

class RosterEmbed(discord.Embed):
    def __init__(self, title=None, description=None):
        super().__init__(title=title, description=description, color=discord.Color.yellow())

class RosterCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    async def roster_listener(self, allycode):
        updates = roster.insert_roster(allycode)
        output = []
        if not updates:
            return
        
        for update in updates:
            update_strings = self.parse_update(update)
            if update_strings:
                output += update_strings
      
    def parse_update(self, update, dictionary):
        db.cursor.execute(f"SELECT u.name FROM units u JOIN roster_units ru ON ru.unit_id = u.unit_id WHERE ru.id = '{update[0]}';")
        unit_name = db.cursor.fetchone()[0]
        if len(update) == 11: #Unit 
            if unit_name not in dictionary:
                dictionary[unit_name] = []
            if update[1] == None:
                dictionary[unit_name].append("Unlocked")
            if update[3] and update[3] != update[4]:
                dictionary[unit_name].append(f"Upgraded from {update[3]}* to {update[4]}*")
            if update[5] != update[6]:
                dictionary[unit_name].append(f"Upgraded from G{update[5] if update[5] else 1} to G{update[6]}")
            if update[7] != update[8]:
                dictionary[unit_name].append(f"Upgraded from R{update[7] if update[7] else 0} to R{update[8]}")
            if not update[9] and update[10]:
                db.cursor.execute(f'''SELECT a.name FROM abilities a JOIN unit_abilities ua ON a.ability_id = ua.ability_id 
                                  JOIN units u ON u.unit_id = ua.unit_id WHERE u.name = '{unit_name}' AND a.ability_id ILIKE 'ultimate%';''')
                ability_name = db.cursor.fetchone()[0]
                dictionary[unit_name].append(f"Unlocked Ultimate - {ability_name}")
            
        elif len(update) == 4: #Ability
            db.cursor.execute(f'''SELECT a.name FROM abilities a WHERE a.skill_id = '{update[1]}';''')
            ability_name = db.cursor.fetchone()[0]
            ability_type = update[1].capitalize().split('skill')[0]
            zeta, omicron = dataloader.get_upgrade_skill_data(update[1], update[2] if update[2] else 1, update[3])
            if unit_name not in dictionary:
                dictionary[unit_name] = []
            if zeta:
                dictionary[unit_name].append(f"Applied Zeta on {ability_name} ({ability_type})")
            if omicron:
                dictionary[unit_name].append(f"Applied Omicron on {ability_name} ({ability_type})")
        return dictionary

    @app_commands.command(name="roster", description="Get a player's roster")
    async def roster(self, interaction: discord.Interaction, allycode: int):
        await interaction.response.defer()
        output = {}
        updates = roster.insert_roster(allycode)
        if updates:
            for update in updates:
                output = self.parse_update(update, output)

        embed = RosterEmbed(title="Upgrades Today")
        description = ""
        field_count = 0
        for name, upgrades in output.items():
            if field_count >= 25: #Max field count (could add followup for more than 25 upgrades but is unlikely to be needed)
                break 
            if 'Unlocked' in upgrades:
                description += f"Unlocked **{name}**\n"
                upgrades.remove('Unlocked')
            embed.add_field(name=name, value='\n'.join(upgrades), inline=False)
            field_count += 1
        
        embed.description = description
        embed.timestamp = datetime.now()
        await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(RosterCog(bot))