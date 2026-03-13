import os
import json
import discord
from discord.ext import commands, tasks
from discord import app_commands, ui
from flask import Flask
from threading import Thread
from datetime import datetime

# -------------------
# Flask keep-alive
# -------------------
app = Flask('')

@app.route('/')
def home():
    return "Bot is running 24/7!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

keep_alive()

# -------------------
# Bot Setup
# -------------------
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree
start_time = datetime.utcnow()

# -------------------
# Settings storage
# -------------------
SETTINGS_FILE = "settings.json"
if os.path.exists(SETTINGS_FILE):
    with open(SETTINGS_FILE, "r") as f:
        settings = json.load(f)
else:
    settings = {}  # server_id: {welcome_channel, goodbye_channel, log_channel, announcement_channel, chatlog_channel}

def save_settings():
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=4)

# -------------------
# Curse word filter
# -------------------
curse_words = ["fuck","shit","bitch","asshole","dick","cunt","pussy","whore"]

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    # Filter
    if any(word in message.content.lower() for word in curse_words):
        try:
            await message.delete()
            await message.channel.send(f"{message.author.mention}, that word is not allowed!", delete_after=5)
        except:
            pass
    # Chat logging
    guild_id = str(message.guild.id)
    if guild_id in settings and "chatlog_channel" in settings[guild_id]:
        log_channel_id = settings[guild_id]["chatlog_channel"]
        log_channel = bot.get_channel(log_channel_id)
        if log_channel:
            await log_channel.send(f"**{message.author}**: {message.content}")
    await bot.process_commands(message)

# -------------------
# Dropdown Select Helper
# -------------------
class ChannelSelect(ui.Select):
    def __init__(self, interaction, purpose):
        options = [discord.SelectOption(label=c.name, value=str(c.id)) for c in interaction.guild.channels if isinstance(c, discord.TextChannel)]
        super().__init__(placeholder="Select a channel...", min_values=1, max_values=1, options=options)
        self.interaction = interaction
        self.purpose = purpose

    async def callback(self, interaction: discord.Interaction):
        guild_id = str(interaction.guild.id)
        if guild_id not in settings:
            settings[guild_id] = {}
        settings[guild_id][self.purpose] = int(self.values[0])
        save_settings()
        await interaction.response.send_message(f"{self.purpose.replace('_',' ').title()} channel set to <#{self.values[0]}>", ephemeral=True)

class ChannelView(ui.View):
    def __init__(self, interaction, purpose):
        super().__init__()
        self.add_item(ChannelSelect(interaction, purpose))

# -------------------
# Core Commands
# -------------------
@tree.command(name="ping", description="Check bot latency")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"Pong! {round(bot.latency*1000)}ms")

@tree.command(name="botinfo", description="Show bot information")
async def botinfo(interaction: discord.Interaction):
    await interaction.response.send_message(
        f"Bot: {bot.user.name}\nID: {bot.user.id}\nUptime: {datetime.utcnow() - start_time}"
    )

@tree.command(name="uptime", description="Show bot uptime")
async def uptime(interaction: discord.Interaction):
    await interaction.response.send_message(f"Uptime: {datetime.utcnow() - start_time}")

# -------------------
# Moderation
# -------------------
@tree.command(name="ban", description="Ban a user")
@app_commands.describe(user="Select a user", reason="Reason")
async def ban(interaction: discord.Interaction, user: discord.Member, reason: str = None):
    await user.ban(reason=reason)
    await interaction.response.send_message(f"{user.mention} has been banned.")

@tree.command(name="kick", description="Kick a user")
@app_commands.describe(user="Select a user", reason="Reason")
async def kick(interaction: discord.Interaction, user: discord.Member, reason: str = None):
    await user.kick(reason=reason)
    await interaction.response.send_message(f"{user.mention} has been kicked.")

@tree.command(name="mute", description="Mute a user (Muted role required)")
@app_commands.describe(user="Select a user")
async def mute(interaction: discord.Interaction, user: discord.Member):
    role = discord.utils.get(interaction.guild.roles, name="Muted")
    if role:
        await user.add_roles(role)
        await interaction.response.send_message(f"{user.mention} has been muted.")
    else:
        await interaction.response.send_message("Muted role not found.", ephemeral=True)

@tree.command(name="unmute", description="Unmute a user")
@app_commands.describe(user="Select a user")
async def unmute(interaction: discord.Interaction, user: discord.Member):
    role = discord.utils.get(interaction.guild.roles, name="Muted")
    if role:
        await user.remove_roles(role)
        await interaction.response.send_message(f"{user.mention} has been unmuted.")
    else:
        await interaction.response.send_message("Muted role not found.", ephemeral=True)

# -------------------
# Welcome / Goodbye
# -------------------
@tree.command(name="setwelcome", description="Select the welcome channel")
async def setwelcome(interaction: discord.Interaction):
    await interaction.response.send_message("Select a channel for welcome messages:", view=ChannelView(interaction, "welcome_channel"), ephemeral=True)

@tree.command(name="setgoodbye", description="Select the goodbye channel")
async def setgoodbye(interaction: discord.Interaction):
    await interaction.response.send_message("Select a channel for goodbye messages:", view=ChannelView(interaction, "goodbye_channel"), ephemeral=True)

# -------------------
# Announcement
# -------------------
@tree.command(name="setannouncement", description="Select announcement channel")
async def setannouncement(interaction: discord.Interaction):
    await interaction.response.send_message("Select a channel for announcements:", view=ChannelView(interaction, "announcement_channel"), ephemeral=True)

@tree.command(name="announcement", description="Send an announcement")
@app_commands.describe(title="Title of announcement", message="Message content")
async def announcement(interaction: discord.Interaction, title: str, message: str):
    guild_id = str(interaction.guild.id)
    if guild_id in settings and "announcement_channel" in settings[guild_id]:
        ch = bot.get_channel(settings[guild_id]["announcement_channel"])
        if ch:
            embed = discord.Embed(title=title, description=message, color=discord.Color.blue())
            await ch.send(embed=embed)
            await interaction.response.send_message("Announcement sent!", ephemeral=True)
            return
    await interaction.response.send_message("Announcement channel not set.", ephemeral=True)

# -------------------
# Chat Logging
# -------------------
@tree.command(name="setchatlog", description="Select chat log channel")
async def setchatlog(interaction: discord.Interaction):
    await interaction.response.send_message("Select a channel for chat logs:", view=ChannelView(interaction, "chatlog_channel"), ephemeral=True)

# -------------------
# Tickets
# -------------------
tickets = {}

@tree.command(name="ticket", description="Open a support ticket")
async def ticket(interaction: discord.Interaction):
    overwrites = {
        interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
        interaction.user: discord.PermissionOverwrite(read_messages=True)
    }
    channel = await interaction.guild.create_text_channel(
        name=f"ticket-{interaction.user.name}",
        overwrites=overwrites
    )
    tickets[interaction.user.id] = channel.id
    await channel.send(f"{interaction.user.mention}, your ticket is ready!")
    await interaction.response.send_message("Ticket created!", ephemeral=True)

@tree.command(name="close", description="Close the current ticket")
async def close(interaction: discord.Interaction):
    if interaction.channel.id in tickets.values():
        await interaction.channel.delete()
    else:
        await interaction.response.send_message("This is not a ticket channel.", ephemeral=True)

# -------------------
# Hosting / Business
# -------------------
@tree.command(name="order", description="Place a hosting order")
async def order(interaction: discord.Interaction):
    await interaction.response.send_message("Visit https://yourpanel.com to place an order!")

@tree.command(name="apply", description="Apply for staff or support")
async def apply(interaction: discord.Interaction):
    await interaction.response.send_message("Fill out the application form: https://yourform.com")

@tree.command(name="plans", description="View hosting plans")
async def plans(interaction: discord.Interaction):
    await interaction.response.send_message("Hosting Plans:\nBasic - $5\nStandard - $10\nPremium - $20")

@tree.command(name="status", description="Check server status")
async def status(interaction: discord.Interaction):
    await interaction.response.send_message("All servers operational ✅")

@tree.command(name="panel", description="Access hosting control panel")
async def panel(interaction: discord.Interaction):
    await interaction.response.send_message("Control Panel: https://yourpanel.com")

@tree.command(name="website", description="Visit website")
async def website(interaction: discord.Interaction):
    await interaction.response.send_message("Website: https://yourwebsite.com")

@tree.command(name="support", description="Open a support ticket")
async def support(interaction: discord.Interaction):
    await interaction.response.send_message("Support: https://support.yourwebsite.com")

# -------------------
# Run Bot
# -------------------
@bot.event
async def on_ready():
    await tree.sync()
    print(f"{bot.user} is online!")

bot.run(os.getenv("TOKEN"))
