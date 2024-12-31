import asyncio
import datetime
from datetime import datetime, timedelta, timezone
import random
import discord
from discord import app_commands
from backend import db, comlink, localization, log

async def unit_autocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    db.cursor.execute("SELECT name FROM units ORDER BY name;")
    units = [app_commands.Choice(name=unit[0], value=unit[0]) for unit in db.cursor.fetchall()]
    return [unit for unit in units if current.lower() in unit.name.lower()][:25]

async def tag_autocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    db.cursor.execute("SELECT name FROM tags ORDER by name;")
    tags = [app_commands.Choice(name=tag[0], value=tag[0]) for tag in db.cursor.fetchall()]
    return [tag for tag in tags if current.lower() in tag.name.lower()][:25]

def allycode_check(allycode):
    """
    Validates input for a valid allycode
    """
    if len(str(allycode)) != 9:
        return "Allycode must be 9 digits long"
    
    result = comlink.get_player(allycode=allycode)
    if "message" in result.keys():
        return f"An account with allycode {allycode} could not be found"
    
    return result

def calculate_payout(offset):
    """
    Calculates the next payout time given an offset
    """
    now = datetime.now(timezone.utc)
    payout = datetime.now(timezone.utc).replace(hour=19, minute=0, second=0, microsecond=0) - timedelta(minutes=offset)
    while now > payout:
        payout += timedelta(days=1)
    return int(payout.timestamp())

def calculate_reset(offset):
    """
    Calculates the next reset time given an offset
    """
    now = datetime.now(timezone.utc)
    reset = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(minutes=offset)
    while now > reset:
        reset += timedelta(days=1)
    return int(reset.timestamp())

def get_events():
    """
    Returns a list of all scheduled events
    """
    result = comlink.get_events(enums=True).get('gameEvent')
    while result is None:
        result = comlink.get_events(enums=True).get('gameEvent')
        asyncio.sleep(1)
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

def get_player_rank(allycode):
    player = comlink.get_player_arena(allycode=allycode, player_details_only=True).get('pvpProfile')
    while player is None:
        player = comlink.get_player_arena(allycode=allycode, player_details_only=True).get('pvpProfile')
        asyncio.sleep(1)
    return player[1]['rank']

async def send_dm(bot, discord_id, embed):
    """
    Helper function to send a DM to a user, retrying up to 5 times if it fails
    Returns the message
    """
    user = bot.get_user(int(discord_id))
    for _ in range(5):
        try:
            message = await user.send(embed=embed)
            log(f"Sent DM to {discord_id}")
            return message
        except discord.errors.Forbidden: #Not allowed
            log(f"Unable to send DM to {discord_id}")
            return None
        except discord.errors.HTTPException: #Opening DM too fast
            log(f"Failed to send DM to {discord_id}, retrying...")
            await asyncio.sleep(random.randint(1, 3))

class EmbedPages(discord.ui.View):
    def __init__(self, embeds, interaction):
        super().__init__(timeout=120)
        self.interaction = interaction
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
    
    async def on_timeout(self):
        self.clear_items()
        await self.interaction.edit_original_response(view=self)
        self.stop()

    async def update_message(self, interaction):
        await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)

    def update_buttons(self):
        self.previous_button.disabled = self.current_page == 0
        self.next_button.disabled = self.current_page == len(self.embeds) - 1