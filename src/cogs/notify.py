import discord
from discord import app_commands
from discord.ext import commands
from backend import db

class NotifyEmbed(discord.Embed):
    def __init__(self, title=None, description=None):
        super().__init__(title=title, description=description, color=discord.Color.dark_gray())

class Notify(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    notify = app_commands.Group(name="notify", description="Notification commands")

    types = ["Payout", "Events", "Roster", "Daily"]
    choices = [app_commands.Choice(name=type, value=type.lower()) for type in types]
    choices.append(app_commands.Choice(name="All", value="all"))
    
    @notify.command(name="toggle", description="Toggle notifications")
    @app_commands.choices(notif_type=choices)
    @app_commands.rename(notif_type='type')
    async def toggle(self, interaction: discord.Interaction, notif_type: str, allycode: str = None):
        """
        Toggle notifications

        Args:
            type (str): The type of notifications to toggle
            allycode (str, optional): The allycode to toggle notifications for or 'all' for all accounts (for multiple linked accounts) 
        """
        embed = NotifyEmbed(title="Success", description="These changes will reflect in the next cycle")
        discord_id = str(interaction.user.id)
        try:
            allycode = int(allycode)
        except: 
            if allycode.lower() != 'all':
                embed.title = "Error"
                embed.description = "Invalid input for allycode"
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
        #Toggle all notifications for all accounts
        if notif_type == "all" and (not allycode or allycode == 'all'): 
            queries = ', '.join([f"notify_{item} = NOT notify_{item}" for item in self.types if item != "Events"])
            await db.execute(f"UPDATE linked_accounts SET {queries} WHERE discord_id = $1", discord_id)

        #Toggle events (part of toggle all)
        if (notif_type == "all" and (not allycode or allycode == 'all')) or notif_type == "events":
            await db.execute("UPDATE discord_users SET notify_events = NOT notify_events where discord_id = $1", discord_id)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        result = await db.fetch("SELECT allycode from linked_accounts WHERE discord_id = $1", discord_id)
        accounts = [row["allycode"] for row in result]

        #Multiple accounts and no allycode parameter
        if not allycode and len(accounts) > 1: 
            embed.title = "Multiple accounts found"
            embed.description = "Please specify which account or enter 'all' in the 'allycode' parameter to toggle all notifications for that type"
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        #Given allycode not in accounts
        if allycode and allycode != 'all' and allycode not in accounts: 
            embed.title = "Error"
            embed.description = "This allycode is not linked to your accounts"
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        #Toggle all account-specific notifications for that allycode
        if notif_type == "all" and allycode in accounts:
            queries = ', '.join([f"notify_{item} = NOT notify_{item}" for item in self.types if item != "Events"])
            await db.execute(f"UPDATE linked_accounts SET {queries} WHERE allycode = $1", allycode)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        column = f"notify_{notif_type}"
        if allycode == 'all': #All accounts
            await db.execute(f"UPDATE linked_accounts SET {column} = NOT {column} WHERE discord_id = $1", discord_id)        
        else:
            if not allycode: #Default to only linked account
                allycode = accounts[0]
            await db.execute(f"UPDATE linked_accounts SET {column} = NOT {column} WHERE allycode = $1", allycode)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @notify.command(name="get", description="Get notifications")
    async def get(self, interaction: discord.Interaction):
        """
        View status for notifications for your Discord account
        """
        embed = NotifyEmbed(title="Your Notifications Settings")
        notifications = {}
        result = await db.fetchval("SELECT notify_events from discord_users WHERE discord_id = $1", str(interaction.user.id))
        notifications["events"] = "Active" if result else "Inactive"
        result = await db.fetch("SELECT allycode, name, notify_payout, notify_daily, notify_roster from linked_accounts WHERE discord_id = $1", str(interaction.user.id))
        notifications["accounts"] = []
        for row in result:
            account = {}
            account["name"] = f"{row['name']} ({row['allycode']})"
            
            account.update(
                {key.lstrip("notify_"): "Active" if value else "Inactive"
                for key, value in row.items() if key.startswith("notify_")}
            )

            notifications["accounts"].append(account)
            
        embed.description = f"Events: {notifications['events']}"
        for account in notifications['accounts']:
            field = "\n".join(f"{key.capitalize()}: {value}" for key, value in account.items() if key != "name")
            embed.add_field(
                name=account["name"],
                value=field
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Notify(bot))