import sys
sys.path.append("..")
import helpers
import discord
from discord import app_commands
from discord.ext import commands

db = helpers.db

class Allycode(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    allycode = app_commands.Group(name="allycode", description="Allycode commands")

    @allycode.command(name="add")
    async def add(self, interaction: discord.Interaction, allycode: int):    
        """
        Add an allycode to your Discord account
        
        Args:
            allycode (int): The allycode of the SWGOH account
        """
        embed = discord.Embed()
        checkQuery = '''
        SELECT * FROM users WHERE allycode = %s
        '''
        db.cursor.execute(checkQuery, (allycode,))
        result = db.cursor.fetchall()
        if len(result) != 0:
            embed.description = "This allycode is already linked to a Discord account"
            await interaction.response.send_message(embed=embed)
            return
        
        result = helpers.allycode_check(allycode)
        if type(result) == str:
            embed.description = result
            await interaction.response.send_message(embed=embed)
            return

        #TODO: Add confirmation
        name = result['name']
        offset = result['localTimeZoneOffsetMinutes']
        discord_id = interaction.user.id
        query = '''
        INSERT INTO users (allycode, discord_id, name, time_offset) VALUES (%s, %s, %s, %s)
        '''
        db.cursor.execute(query, (allycode, discord_id, name, offset))
        db.connection.commit()
        await interaction.response.send_message(f"**{name}** ({allycode}) is now linked to your Discord account")

    @allycode.command(name="get")
    async def get(self, interaction: discord.Interaction):
        """
        Get all allycodes linked to your Discord account
        """
        query = '''
        SELECT allycode, name FROM users WHERE discord_id = %s
        '''
        db.cursor.execute(query, (str(interaction.user.id),))
        result = db.cursor.fetchall()
        embed = discord.Embed(title="Your allycodes")
        if len(result) == 0:
            embed.description = "You have no allycodes linked to your Discord account"
        else:
            for allycode, name in result:
                embed.add_field(name=allycode, value=name, inline=False)
        await interaction.response.send_message(embed=embed)
    
    @allycode.command(name="remove")
    async def allycode_remove(self, interaction: discord.Interaction, allycode: int):
        """
        Remove an allycode from your Discord account

        Args:
            allycode (int): The allycode of the SWGOH account
        """
        query = '''
        DELETE FROM users WHERE discord_id = %s
        '''
        db.cursor.execute(query, (allycode, str(interaction.user.id),))
        db.connection.commit()
        if db.cursor.rowcount == 0:
            await interaction.response.send_message("This allycode is not linked to your Discord account")
        else:
            await interaction.response.send_message("This allycode has been removed from your Discord account")
        
async def setup(bot):
    await bot.add_cog(Allycode(bot))