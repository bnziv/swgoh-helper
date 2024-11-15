import discord
from discord import app_commands
from database import Database

db = Database()

db.cursor.execute("SELECT name FROM units ORDER BY name;")
unitsQuery = db.cursor.fetchall()
units = [app_commands.Choice(name=unit[0], value=unit[0]) for unit in unitsQuery]

async def unit_autocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    return [unit for unit in units if current.lower() in unit.name.lower()][:25]