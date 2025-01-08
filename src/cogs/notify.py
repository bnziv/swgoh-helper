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