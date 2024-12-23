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
        super().__init__()(title=title, description=description, color=discord.Color.yellow())

class RosterCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    async def roster_listener(self, allycode):
        updates = roster.insert_roster(allycode)
        
        if not updates:
            return
        
        for update in updates:
            pass
            
    def parse_update(self, update):
        update_strings = []
        if len(update) == 11: #Unit 
            name = update[0]
            if update[1] == None:
                update_strings.append(f"Unlocked {name}")
            if update[3] and update[3] != update[4]:
                update_strings.append(f"Upgraded {name} from {update[3]}* to {update[4]}*")
            if update[5] != update[6]:
                update_strings.append(f"Upgraded {name} from G{update[5] if update[5] else 1} to G{update[6]}")
            if update[7] != update[8]:
                update_strings.append(f"Upgraded {name} from R{update[7] if update[7] else 0} to R{update[8]}")
            if not update[9] and update[10]:
                update_strings.append(f"Unlocked ultimate for{name}")
            
        elif len(update) == 3: #Ability
            if update[1] != update[2]:
                name = update[0]
                zeta, omicron = dataloader.get_upgrade_skill_data(update[0], update[1] if update[1] else 1, update[2])
                if zeta:
                    update_strings.append(f"Applied zeta on {name}")
                if omicron:
                    update_strings.append(f"Applied omicron on {name}")
        return update_strings

    @app_commands.command(name="roster", description="Get a player's roster")
    async def roster(self, interaction: discord.Interaction, allycode: int):
        await interaction.response.defer()
        updates = roster.insert_roster(allycode)
        test_array = []
        if updates:
            for update in updates:
                test_array +=self.parse_update(update)
        await interaction.followup.send(test_array)

async def setup(bot):
    await bot.add_cog(RosterCog(bot))