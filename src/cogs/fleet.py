import backend.helpers as helpers
import discord
from discord import app_commands
from discord.ext import commands

db = helpers.db
fleetpayout = helpers.fleetpayout

class FleetEmbed(discord.Embed):
    def __init__(self, title=None, description=None):
        super().__init__(title=title, description=description, color=discord.Color.purple())

class Fleet(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    fleet = app_commands.Group(name="fleet", description="Fleet arena commands")

    @fleet.command(name="get")
    async def get(self, interaction: discord.Interaction, allycode: int = None, name: str = None, all: bool = False):
        """
        Get player's fleet payout time

        Args:
            allycode (int): The allycode of the player
            name (str): The name of the player (if they've been added to your shard)
            all (bool): Get all players' fleet payout times in your shard
        """
        embed = FleetEmbed(title="Fleet Payout Time")
        if allycode is None and name is None and not all:
            embed.description = "Please provide an allycode or name\nNames will only work if they've been added to your shard"
            await interaction.response.send_message(embed=embed)
            return
        
        #All flag
        #TODO: Handle more than 25 entries since embed field max is 25
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
            await interaction.response.send_message(embed=embed)
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
            await interaction.response.send_message(embed=embed)
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
                await interaction.response.send_message(embed=embed)
                return
            name = result['name']
            offset = result['localTimeZoneOffsetMinutes']
            embed.description = "(This player is not in your fleet shard)"
        embed.add_field(
            name = f"**{name}** ({allycode})",
            value = f"<t:{helpers.calculate_payout(offset)}:t>"
            )
        await interaction.response.send_message(embed=embed)

    @fleet.command(name="add")
    async def add(self, interaction: discord.Interaction, allycode: int):
        """
        Add a player to your fleet shard
        
        Args:
            allycode (int): The allycode of the player
        """
        embed = FleetEmbed()
        result = helpers.allycode_check(allycode)
        if type(result) == str:
            embed.description = result
            await interaction.response.send_message(embed=embed)
            return
        name = result['name']
        offset = result['localTimeZoneOffsetMinutes']
        db.cursor.execute('''SELECT allycode from users WHERE discord_id = %s''', (str(interaction.user.id),))
        result = db.cursor.fetchall()
        if len(result) == 0:
            embed.description = "Your Discord account is not linked to an allycode"
        else:
            #TODO: Add multi-account functionality (if len(result) > 1)
            account_allycode = result[0][0]
            fleetpayout.add_player(allycode, name, offset, account_allycode)
            embed.description = f"**{name}** ({allycode}) has been added to your fleet shard"
        await interaction.response.send_message(embed=embed)

    @fleet.command(name="remove")
    async def remove(self, interaction: discord.Interaction, allycode: int):
        """
        Remove a player from your fleet shard
        
        Args:
            allycode (int): The allycode of the player
        """
        embed = FleetEmbed()
        if len(str(allycode)) != 9:
            embed.description = "Allycode must be 9 digits long"
            await interaction.response.send_message(embed=embed)
            return
        
        if fleetpayout.remove_player(allycode):
            embed.description = f"**{allycode}** has been removed from your fleet shard"
        else:
            embed.description = f"**{allycode}** could not be found in your fleet shard"
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Fleet(bot))