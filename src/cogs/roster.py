from backend import db, roster, log
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
      
    async def parse_update(self, update, dictionary):
        unit_name = await db.fetchval(f"SELECT u.name FROM units u JOIN roster_units ru ON ru.unit_id = u.unit_id WHERE ru.id = '{update['unit_id']}';")
        if len(update) == 9: #Unit 
            if unit_name not in dictionary:
                dictionary[unit_name] = []
            if update['old_star'] == None:
                dictionary[unit_name].append("Unlocked")
            if update['old_star'] and update['old_star'] != update['new_star']:
                dictionary[unit_name].append(f"Upgraded from {update['old_star']}* to {update['new_star']}*")
            if update['old_gear'] != update['new_gear']:
                dictionary[unit_name].append(f"Upgraded from G{update['old_gear'] if update['old_gear'] else 1} to G{update['new_gear']}")
            if update['old_relic'] != update['new_relic']:
                dictionary[unit_name].append(f"Upgraded from R{update['old_relic'] if update['old_relic'] else 0} to R{update['new_relic']}")
            if not update['old_ultimate'] and update['new_ultimate']:
                ultimate_name = await db.fetchval(f'''SELECT a.name FROM abilities a JOIN unit_abilities ua ON a.ability_id = ua.ability_id 
                                  JOIN units u ON u.unit_id = ua.unit_id WHERE u.name = '{unit_name}' AND a.ability_id ILIKE 'ultimate%';''')
                dictionary[unit_name].append(f"Unlocked Ultimate - {ultimate_name}")
            
        elif len(update) == 4: #Ability
            ability_name = await db.fetchval(f'''SELECT a.name FROM abilities a WHERE a.skill_id = '{update['skill_id']}';''')
            ability_type = update['skill_id'].capitalize().split('skill')[0]
            zeta, omicron = await roster.get_upgrade_skill_data(update['skill_id'], update['old_level'] if update['old_level'] else 1, update['new_level'])
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
        log(f"Roster check for {name} in {delay} seconds/{datetime.fromtimestamp(reset_time).strftime('%H:%M:%S')}")
        await asyncio.sleep(delay)

        output = {}
        updates = await roster.insert_roster(allycode)
        if updates:
            for update in updates:
                output = await self.parse_update(update, output)
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
                if len(upgrades) == 0:
                    continue
            embed.add_field(name=unit_name, value='\n'.join(upgrades), inline=False)
            field_count += 1
        
        embed.description = description
        embed.timestamp = datetime.now()
        await helpers.send_dm(bot=self.bot, discord_id=discord_id, embed=embed)

    @tasks.loop(time=helpers.DAILY_LOOP)
    async def start_listeners(self):
        result = await db.fetch("SELECT allycode, discord_id, name, time_offset FROM linked_accounts WHERE notify_roster IS TRUE")
        for row in result:
            user = (row['allycode'], row['discord_id'], row['name'], row['time_offset'])
            asyncio.create_task(self.roster_listener(*user))

    @commands.Cog.listener()
    async def on_ready(self):
        self.start_listeners.start()

async def setup(bot):
    await bot.add_cog(RosterCog(bot))