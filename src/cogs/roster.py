from backend import db, dataloader, roster
import backend.helpers as helpers
import asyncio
from datetime import datetime
import discord
from discord.ext import commands, tasks

class RosterEmbed(discord.Embed):
    def __init__(self, title=None, description=None):
        super().__init__(title=title, description=description, color=discord.Color.yellow())

class RosterCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
      
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
            if (zeta or omicron) and unit_name not in dictionary:
                dictionary[unit_name] = []
            if zeta:
                dictionary[unit_name].append(f"Applied Zeta on {ability_name} ({ability_type})")
            if omicron:
                dictionary[unit_name].append(f"Applied Omicron on {ability_name} ({ability_type})")
        return dictionary

    async def roster_listener(self, allycode, discord_id, name, offset):
        reset_time = helpers.calculate_reset(offset)
        current = int(datetime.now().timestamp())
        delay = reset_time - current
        await asyncio.sleep(delay)

        output = {}
        updates = roster.insert_roster(allycode)
        if updates:
            for update in updates:
                output = self.parse_update(update, output)
        else:
            return

        embed = RosterEmbed(title=f"{name}'s upgrades since last reset")
        description = ""
        field_count = 0
        for unit_name, upgrades in output.items():
            if field_count >= 25: #Max field count (could add followup for more than 25 upgrades but is unlikely to be needed)
                break 
            if 'Unlocked' in upgrades:
                description += f"Unlocked **{unit_name}**\n"
                upgrades.remove('Unlocked')
            embed.add_field(name=unit_name, value='\n'.join(upgrades), inline=False)
            field_count += 1
        
        embed.description = description
        embed.timestamp = datetime.now()
        await helpers.send_dm(bot=self.bot, discord_id=discord_id, embed=embed)

    @tasks.loop(hours=24)
    async def start_listeners(self):
        db.cursor.execute("SELECT allycode, discord_id, name, time_offset FROM linked_accounts WHERE notify_roster IS TRUE")
        for result in db.cursor.fetchall():
            asyncio.create_task(self.roster_listener(*result))

    @commands.Cog.listener()
    async def on_ready(self):
        self.start_listeners.start()

async def setup(bot):
    await bot.add_cog(RosterCog(bot))