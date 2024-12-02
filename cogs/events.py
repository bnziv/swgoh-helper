import sys
sys.path.append("..")
import helpers
import re
from datetime import datetime
import discord
from discord import app_commands
from discord.ext import commands, tasks
from titlecase import titlecase
import asyncio

comlink = helpers.comlink
db = helpers.db

class EventsEmbed(discord.Embed):
    def __init__(self, title=None, description=None):
        super().__init__(title=title, description=description, color=discord.Color.orange())

class Events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    events = app_commands.Group(name="events", description="Events commands")

    def capitalize_title(self, title: str):
        title = titlecase(title)
        roman_numeral_pattern = r'\b(?:I{1,3}|IV|VI{0,3}|IX|X{0,3})\b'

        def roman_numeral(word):
            return word.upper() if re.fullmatch(roman_numeral_pattern, word.upper()) else word
        
        words = [roman_numeral(word) for word in title.split()]
        return ' '.join(words)

    @events.command(name="current")
    @app_commands.checks.cooldown(1,60)
    async def current(self, interaction: discord.Interaction, embeds: bool = False):
        """
        Get all current game events

        Args:
            embeds (bool): Show the events in pages of embeds rather than a list (Default: False)
        """
        await interaction.response.send_message("Fetching events...")
        currentTime = int(datetime.now().timestamp())
        events = [e for e in helpers.get_events() if currentTime >= e['startTime'] and currentTime < e['endTime']]
        events = sorted(events, key=lambda e: e['endTime'])
        if not embeds:
            embed = EventsEmbed(title="Currently Running Events")
            for event in events:
                title, subtitle = event['name'].split('\\n')
                subtitle = re.sub(r'\[c\]\[.*?\]|\[-\]\[/c\]', '', subtitle)
                desc = event['desc']
                embed.add_field(name=f"{self.capitalize_title(title)} - {subtitle}",
                                value=f"Ends <t:{event['endTime']}:R>",
                                inline=False
                )
            await interaction.edit_original_response(content=None, embed=embed)
        else:
            embeds = []
            for event in events:
                title, subtitle = event['name'].split('\\n')
                subtitle = re.sub(r'\[c\]\[.*?\]|\[-\]\[/c\]', '', subtitle)
                desc = event['desc']
                embed = EventsEmbed(title=f"{self.capitalize_title(title)}\n{subtitle}", description=desc)
                embed.add_field(name="Start Time", value=f"<t:{event['startTime']}>")
                embed.add_field(name="End Time", value=f"<t:{event['endTime']}>")
                embed.set_image(url=f"https://game-assets.swgoh.gg/textures/{event['image']}.png")
                embeds.append(embed)
            view = helpers.EmbedPages(embeds, interaction=interaction)
            await interaction.edit_original_response(content=None, embed=embeds[0], view=view)
    
    @current.error
    async def current_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message(f"Command is on cooldown for {round(error.retry_after)} seconds", ephemeral=True)
    
    @events.command(name="upcoming")
    @app_commands.checks.cooldown(1,60)
    async def upcoming(self, interaction: discord.Interaction, embeds: bool = False):
        """
        Get all upcoming game events

        Args:
            embeds (bool): Show the events in pages of embeds rather than a list (Default: False)
        """
        await interaction.response.send_message("Fetching events...")
        currentTime = int(datetime.now().timestamp())
        events = [e for e in helpers.get_events() if currentTime < e['startTime']]
        events = sorted(events, key=lambda e: e['endTime'])
        if not embeds:
            embed = EventsEmbed(title="Upcoming Events")
            for event in events:
                title, subtitle = event['name'].split('\\n')
                subtitle = re.sub(r'\[c\]\[.*?\]|\[-\]\[/c\]', '', subtitle)
                desc = event['desc']
                embed.add_field(name=f"{self.capitalize_title(title)} - {subtitle}",
                                value=f"Starts <t:{event['startTime']}:R>",
                                inline=False
                )
            await interaction.edit_original_response(content=None, embed=embed)
        else:
            embeds = []
            for event in events:
                title, subtitle = event['name'].split('\\n')
                subtitle = re.sub(r'\[c\]\[.*?\]|\[-\]\[/c\]', '', subtitle)
                desc = event['desc']
                embed = EventsEmbed(title=f"{self.capitalize_title(title)}\n{subtitle}", description=desc)
                embed.add_field(name="Start Time", value=f"<t:{event['startTime']}>")
                embed.add_field(name="End Time", value=f"<t:{event['endTime']}>")
                embed.set_image(url=f"https://game-assets.swgoh.gg/textures/{event['image']}.png")
                embeds.append(embed)
            view = helpers.EmbedPages(embeds, interaction=interaction)
            await interaction.edit_original_response(content=None, embed=embeds[0], view=view)
    
    @upcoming.error
    async def upcoming_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message(f"Command is on cooldown for {round(error.retry_after)} seconds", ephemeral=True)

    @tasks.loop(hours=1)
    async def started_events_listener(self):
        currentTime = int(datetime.now().timestamp())
        events = [e for e in helpers.get_events() 
                  if e['startTime'] in range(currentTime - 5, currentTime + 5)] #Time margin of error
        
        if events:
            db.cursor.execute("SELECT DISTINCT discord_id FROM users WHERE notify_events IS TRUE")
            users = [self.bot.get_user(int(id[0])) for id in db.cursor.fetchall()]

            embed = EventsEmbed(description="The following events started: ")
            for event in events:
                title, subtitle = event['name'].split('\\n')
                subtitle = re.sub(r'\[c\]\[.*?\]|\[-\]\[/c\]', '', subtitle)
                embed.add_field(name=f"{self.capitalize_title(title)} - {subtitle}",
                                value=f"Ends <t:{event['endTime']}:R>",
                                inline=False
                )
            
            tasks = [user.send(embed=embed) for user in users]
            await asyncio.gather(*tasks)
          
    @commands.Cog.listener()
    async def on_ready(self):
        #Align events listener to the next hour
        now = datetime.now()
        if now.minute != 0 or now.second != 0:
            delay = (3600 - (now.minute * 60 + now.second))
            await asyncio.sleep(delay)
        self.started_events_listener.start()

async def setup(bot):
    await bot.add_cog(Events(bot))