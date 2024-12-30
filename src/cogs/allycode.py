import asyncio
from backend import db, roster, queries
import backend.helpers as helpers
import discord
from discord import app_commands
from discord.ext import commands

class AllycodeEmbed(discord.Embed):
    def __init__(self, title=None, description=None):
        super().__init__(title=title, description=description, color=discord.Color.lighter_gray())

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
        embed = AllycodeEmbed()
        discord_id = interaction.user.id
        checkQuery = '''
        SELECT allycode, discord_id FROM linked_accounts WHERE allycode = %s
        '''
        db.cursor.execute(checkQuery, (allycode,))
        result = db.cursor.fetchall()
        if len(result) != 0:
            if int(result[0][1]) == discord_id:
                embed.description = "This allycode is already linked to your Discord account"
            else:
                embed.description = "This allycode is already linked to another Discord account"
            await interaction.response.send_message(embed=embed)
            return
        
        result = helpers.allycode_check(allycode)
        if type(result) == str:
            embed.description = result
            await interaction.response.send_message(embed=embed)
            return

        name = result['name']
        offset = result['localTimeZoneOffsetMinutes']
        if result['selectedPlayerPortrait']:
            portrait_id = result['selectedPlayerPortrait']['id']
        else:
            portrait_id = "PLAYERPORTRAIT_DEFAULT"
        db.cursor.execute("SELECT icon FROM portraits WHERE id = %s", (portrait_id,))
        portrait = db.cursor.fetchone()[0]

        embed.title = f"Confirmation"
        embed.description = f"Are you sure you want to link **{name}** ({allycode}) to your Discord account?"
        embed.set_thumbnail(url=f"https://game-assets.swgoh.gg/textures/{portrait}.png")
        
        guild = result['guildName']
        if guild:
            embed.add_field(name="Guild", value=guild)

        #Hard coding rank as opposed to referencing through comlink calls
        rank_data = result['playerRating']['playerRankStatus']
        if rank_data:
            league = rank_data['leagueId'].capitalize()
            division = 6 - rank_data['divisionId']//5
            embed.add_field(name=f"{league}", value=f"Division {division}")
        
        await interaction.response.send_message(embed=embed)
        confirmation = await interaction.original_response()
        await confirmation.add_reaction("✅")
        try:
            def check(reaction, reactor):
                return (discord_id == reactor.id and str(reaction.emoji) == "✅" and reaction.message.id == confirmation.id)
            await self.bot.wait_for("reaction_add", timeout=30, check=check)
        except asyncio.TimeoutError:
            await confirmation.delete()
            return
        
        db.cursor.execute(queries.insert_discord_user, (discord_id,))
        db.cursor.execute(queries.insert_linked_account, (allycode, discord_id, name, offset))
        roster.insert_roster(allycode, update=False)
        db.connection.commit()
        embed.title = "Success"
        embed.description = f"**{name}** ({allycode}) is now linked to your Discord account"
        await interaction.edit_original_response(embed=embed)

    @allycode.command(name="get")
    async def get(self, interaction: discord.Interaction):
        """
        Get all allycodes linked to your Discord account
        """
        query = '''
        SELECT allycode, name FROM linked_accounts WHERE discord_id = %s
        '''
        db.cursor.execute(query, (str(interaction.user.id),))
        result = db.cursor.fetchall()
        embed = AllycodeEmbed(title="Your allycodes")
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
        DELETE FROM linked_accounts WHERE allycode = %s AND discord_id = %s
        '''
        db.cursor.execute(query, (allycode, str(interaction.user.id),))
        db.connection.commit()
        if db.cursor.rowcount == 0:
            await interaction.response.send_message("This allycode is not linked to your Discord account")
        else:
            await interaction.response.send_message("This allycode has been removed from your Discord account")
        
async def setup(bot):
    await bot.add_cog(Allycode(bot))