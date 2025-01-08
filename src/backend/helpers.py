import asyncio
import datetime
from datetime import datetime, timedelta, timezone, time
import random
import discord
from discord import app_commands
from backend import db, comlink, log, dataloader

DAILY_LOOP = time(23, 59, 30, tzinfo=timezone.utc) #Loop 30 seconds before midnight as a buffer
HOURLY_LOOP = [time(h, 0, 0, tzinfo=timezone.utc) for h in range(24)]
UPDATE_LOOP = [time(h, 30, 0, tzinfo=timezone.utc) for h in range(24)]

CACHE_WINDOW = timedelta(minutes=5)

UNIT_CACHE = {"units": [], "updated": None}
async def unit_autocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    global UNIT_CACHE

    if not UNIT_CACHE["units"] or (datetime.now(timezone.utc) - UNIT_CACHE["updated"]) > CACHE_WINDOW:
        results = await db.fetch("SELECT name FROM units ORDER BY name")
        UNIT_CACHE["units"] = [row['name'] for row in results]
        UNIT_CACHE["updated"] = datetime.now(timezone.utc)
    
    matches = [unit for unit in UNIT_CACHE["units"] if current.lower() in unit.lower()]
    return [app_commands.Choice(name=match, value=match) for match in matches][:25]

TAG_CACHE = {"tags": [], "updated": None}
async def tag_autocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    global TAG_CACHE

    if not TAG_CACHE["tags"] or (datetime.now(timezone.utc) - TAG_CACHE["updated"]) > CACHE_WINDOW:
        results = await db.fetch("SELECT name FROM tags ORDER BY name")
        TAG_CACHE["tags"] = [row['name'] for row in results]
        TAG_CACHE["updated"] = datetime.now(timezone.utc)

    matches = [tag for tag in TAG_CACHE["tags"] if current.lower() in tag.lower()]
    return [app_commands.Choice(name=match, value=match) for match in matches][:25]

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

async def get_events():
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
            "name": await dataloader.get_localization(e["nameKey"]),
            "desc": await dataloader.get_localization(e["descKey"]),
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
    user = await bot.fetch_user(int(discord_id))
    if not user:
        log(f"Could not get user {discord_id}", "error")
        return
    for _ in range(5):
        try:
            message = await user.send(embed=embed)
            log(f"Sent DM to {discord_id}")
            return message
        except discord.errors.Forbidden: #Not allowed
            log(f"Unable to send DM to {discord_id}", "error")
            return None
        except discord.errors.HTTPException: #Opening DM too fast
            log(f"Failed to send DM to {discord_id}, retrying...", "warning")
            await asyncio.sleep(random.randint(1, 3))
    return None

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