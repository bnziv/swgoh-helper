import datetime
from datetime import datetime, timedelta, timezone
import discord
from discord import app_commands
import pytz
from database import Database
from swgoh_comlink import SwgohComlink
from fleetpayout import FleetPayout
from dataloader import DataLoader

db = Database()
comlink = SwgohComlink()
dataloader = DataLoader(db, comlink)
fleetpayout = FleetPayout(db, comlink)

localization = dataloader.get_localization()

db.cursor.execute("SELECT name FROM units ORDER BY name;")
units = [app_commands.Choice(name=unit[0], value=unit[0]) for unit in db.cursor.fetchall()]
async def unit_autocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    return [unit for unit in units if current.lower() in unit.name.lower()][:25]

db.cursor.execute("SELECT name FROM tags ORDER by name;")
tags = [app_commands.Choice(name=tag[0], value=tag[0]) for tag in db.cursor.fetchall()]
async def tag_autocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    return [tag for tag in tags if current.lower() in tag.name.lower()][:25]

def allycode_check(allycode):
    if len(str(allycode)) != 9:
        return "Allycode must be 9 digits long"
    
    result = comlink.get_player_arena(allycode=allycode, player_details_only=True)
    if "message" in result.keys():
        return f"An account with allycode {allycode} could not be found"
    
    return result

def calculate_payout(offset):
    payout = datetime.now(timezone.utc).replace(hour=19, minute=0, second=0, microsecond=0) - timedelta(minutes=offset)
    return int(payout.timestamp())

def calculate_reset(offset):
    reset = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(minutes=offset)
    return int(reset.timestamp())

def get_events():
    """
    Returns a list of all scheduled events
    """
    result = comlink.get_events(enums=True)['gameEvent']
    result = [r for r in result if 'challenge' not in r['id'] and 'shipevent_SC' not in r['id'] and 'GA2' not in r['id'] and r['type'] == "SCHEDULED"]
    events = []
    for e in result:
        event = {
            "name": localization[e["nameKey"]],
            "desc": localization[e["descKey"]],
            "startTime": int(e['instance'][0]['startTime'])//1000,
            "endTime": int(e['instance'][0]['endTime'])//1000,
            "image": e['image']
        }
        events.append(event)
    return events

class EmbedPages(discord.ui.View):
    def __init__(self, embeds):
        super().__init__()
        self.embeds = embeds
        self.current_page = 0

        self.previous_button = discord.ui.Button(label="Previous", style=discord.ButtonStyle.primary)
        self.next_button = discord.ui.Button(label="Next", style=discord.ButtonStyle.primary)
        self.done_button = discord.ui.Button(label="Done", style=discord.ButtonStyle.secondary)
        
        self.add_item(self.previous_button)
        self.add_item(self.next_button)
        self.add_item(self.done_button)

        self.next_button.callback = self.next_page
        self.previous_button.callback = self.previous_page
        self.done_button.callback = self.done

        self.update_buttons()

    async def previous_page(self, interaction):
        if self.current_page > 0:
            self.current_page -= 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)
    
    async def next_page(self, interaction):
        if self.current_page < len(self.embeds) - 1:
            self.current_page += 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)

    async def done(self, interaction):
        self.clear_items()
        await interaction.response.edit_message(view=self)
        self.stop()

    async def update_message(self, interaction):
        await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)

    def update_buttons(self):
        self.previous_button.disabled = self.current_page == 0
        self.next_button.disabled = self.current_page == len(self.embeds) - 1