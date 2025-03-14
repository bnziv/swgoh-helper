from backend import db
import backend.helpers as helpers
import re
from datetime import datetime
import discord
from discord import app_commands
from discord.ext import commands, tasks
from titlecase import titlecase
import asyncio

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
    
    def events_to_embed(self, events, type, embed_flag = False):
        embed_title = embed_desc = None
        if type == "upcoming":
            embed_title = "Upcoming Events"
            embed_field = "Starts"
            time_key = "startTime"
        elif type == "current":
            embed_title = "Currently Running Events"
            embed_field = "Ends"
            time_key = "endTime"
        elif type == "started":
            embed_desc = "The following events started: "
            embed_field = "Ends"
            time_key = "endTime"
        
        if not embed_flag:
            embed = EventsEmbed(title=embed_title, description=embed_desc)
            for event in events:
                if '\\n' in event['name']:
                    title, subtitle = event['name'].split('\\n')
                else:
                    title = event['name']
                    subtitle = ''
                subtitle = re.sub(r'\[c\]\[.*?\]|\[-\]\[/c\]', '', subtitle)
                subtitle_text = f" - {subtitle}" if subtitle else ''
                field_title = f"{self.capitalize_title(title)}{subtitle_text}"
                embed.add_field(name=f"{field_title}",
                                value=f"{embed_field} <t:{event[time_key]}:R>",
                                inline=False
                )
            return embed
        else:
            embeds = []
            for event in events:
                if '\\n' in event['name']:
                    title, subtitle = event['name'].split('\\n')
                else:
                    title = event['name']
                    subtitle = ''
                subtitle = re.sub(r'\[c\]\[.*?\]|\[-\]\[/c\]', '', subtitle)
                desc = event['desc']
                embed = EventsEmbed(title=f"{self.capitalize_title(title)}\n{subtitle}", description=desc)
                embed.add_field(name="Start Time", value=f"<t:{event['startTime']}>")
                embed.add_field(name="End Time", value=f"<t:{event['endTime']}>")
                embed.set_image(url=f"https://game-assets.swgoh.gg/textures/{event['image']}.png")
                embeds.append(embed)
            return embeds
            
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
        events = [e for e in await helpers.get_events() if currentTime >= e['startTime'] and currentTime < e['endTime']]
        events = sorted(events, key=lambda e: e['endTime'])
        if not embeds:
            embed = self.events_to_embed(events=events, type="current", embed_flag=embeds)
            await interaction.edit_original_response(content=None, embed=embed)
        else:
            embeds = self.events_to_embed(events=events, type="current", embed_flag=embeds)
            view = helpers.EmbedPages(embeds, interaction=interaction)
            await interaction.edit_original_response(content=None, embed=embeds[0], view=view)
    
    @current.error
    async def current_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message(f"Command is on cooldown for {round(error.retry_after)} seconds", ephemeral=True)
        else:
            await interaction.edit_original_response(content="Something went wrong")
            print(error)
    
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
        events = [e for e in await helpers.get_events() if currentTime < e['startTime']]
        events = sorted(events, key=lambda e: e['endTime'])
        if not embeds:
            embed = self.events_to_embed(events=events, type="upcoming", embed_flag=embeds)
            await interaction.edit_original_response(content=None, embed=embed)
        else:
            embeds = self.events_to_embed(events=events, type="upcoming", embed_flag=embeds)
            view = helpers.EmbedPages(embeds, interaction=interaction)
            await interaction.edit_original_response(content=None, embed=embeds[0], view=view)
    
    @upcoming.error
    async def upcoming_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message(f"Command is on cooldown for {round(error.retry_after)} seconds", ephemeral=True)
        else:
            await interaction.edit_original_response(content="Something went wrong")
            print(error)

    @tasks.loop(time=helpers.HOURLY_LOOP)
    async def started_events_listener(self):
        currentTime = int(datetime.now().timestamp())
        events = [e for e in await helpers.get_events() 
                  if e['startTime'] in range(currentTime - 5, currentTime + 5)] #Time margin of error
        if events:
            result = await db.fetch("SELECT discord_id FROM discord_users WHERE notify_events IS TRUE")
            embed = self.events_to_embed(events=events, type="started")
            for user in result:
                await helpers.send_dm(bot=self.bot, discord_id=user['discord_id'], embed=embed)

    @commands.Cog.listener()
    async def on_ready(self):
        self.started_events_listener.start()

async def setup(bot):
    await bot.add_cog(Events(bot))