import discord
from discord import app_commands
from database import Database

db = Database()

db.cursor.execute("SELECT name FROM units ORDER BY name;")
unitsQuery = db.cursor.fetchall()
units = [app_commands.Choice(name=unit[0], value=unit[0]) for unit in unitsQuery]

async def unit_autocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    return [unit for unit in units if current.lower() in unit.name.lower()][:25]

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